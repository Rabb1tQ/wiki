import os
import re
import shutil
from elasticsearch import Elasticsearch
import markdown2
import uuid
from datetime import datetime

MD_DIR = 'markdown'  # 你的 Markdown 文件目录
IMG_DIR = 'static/uploads/images'
ATT_DIR = 'static/uploads/attachments'
INDEX_NAME = 'wiki_docs'

es = Elasticsearch(
    ['http://192.168.239.136:9200'],
    http_auth=('elastic', 'changeme')
)


def create_index():
    """创建索引并设置映射"""
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
    
    es.indices.create(
        index=INDEX_NAME,
        mappings={
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                    "search_analyzer": "ik_smart",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "content": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                    "search_analyzer": "ik_smart"
                },
                "category": {
                    "type": "keyword"
                },
                "update_time": {
                    "type": "date",
                    "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"
                },
                "views": {
                    "type": "integer"
                },
                "attachments": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "keyword"},
                        "url": {"type": "keyword"}
                    }
                }
            }
        },
        settings={
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
    )
    print(f"索引 {INDEX_NAME} 创建成功")


def ensure_dirs():
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(ATT_DIR, exist_ok=True)


def extract_title(content, md_path):
    # 优先用markdown第一行#标题作为title
    for line in content.splitlines():
        m = re.match(r'^#\s+(.+)', line.strip())
        if m:
            return m.group(1)
    # 如果是index.md则用上级目录名
    if os.path.basename(md_path).lower() == 'index.md':
        return os.path.basename(os.path.dirname(md_path))
    # 否则用文件名
    return os.path.splitext(os.path.basename(md_path))[0]


def get_category(md_path):
    # 获取相对MD_DIR的目录结构
    rel_path = os.path.relpath(md_path, MD_DIR)
    parts = rel_path.split(os.sep)
    if len(parts) > 1:
        return os.path.join(*parts[:-1])
    return ''


def parse_and_copy(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    title = extract_title(content, md_path)
    category = get_category(md_path)
    attachments = []

    # 处理图片 ![alt](path)
    def img_repl(match):
        img_path = match.group(2)
        if not os.path.isabs(img_path):
            img_path = os.path.join(os.path.dirname(md_path), img_path)
        if os.path.exists(img_path):
            orig_fname = os.path.basename(img_path)
            ext = os.path.splitext(orig_fname)[1]
            uuid_fname = f"{uuid.uuid4().hex}{ext}"
            dest = os.path.join(IMG_DIR, uuid_fname)
            shutil.copyfile(img_path, dest)
            url = f"/uploads/images/{uuid_fname}"
            return f"![{match.group(1)}]({url})"
        return match.group(0)

    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', img_repl, content)

    # 处理附件 [desc](path)
    def att_repl(match):
        att_path = match.group(2)
        if not os.path.isabs(att_path):
            att_path = os.path.join(os.path.dirname(md_path), att_path)
        if os.path.exists(att_path):
            orig_fname = os.path.basename(att_path)
            ext = os.path.splitext(orig_fname)[1]
            uuid_fname = f"{uuid.uuid4().hex}{ext}"
            dest = os.path.join(ATT_DIR, uuid_fname)
            shutil.copyfile(att_path, dest)
            url = f"/uploads/attachments/{uuid_fname}"
            attachments.append({'name': orig_fname, 'url': url})
            return f"[{match.group(1)}]({url})"
        return match.group(0)

    content = re.sub(r'\[([^\]]+)\]\(([^)]+\.(pdf|docx?|zip|rar|xls[xm]?|ppt[xm]?|txt|csv))\)', att_repl, content,
                     flags=re.I)

    return {
        'title': title,
        'content': content,
        'attachments': attachments,
        'category': category,
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'views': 0
    }


def import_incremental():
    ensure_dirs()
    # 如果索引不存在，自动新建
    if not es.indices.exists(index=INDEX_NAME):
        print(f"索引 {INDEX_NAME} 不存在，自动创建...")
        create_index()
    for root, dirs, files in os.walk(MD_DIR):
        for file in files:
            if file.endswith('.md'):
                md_path = os.path.join(root, file)
                rel_path = os.path.relpath(md_path, MD_DIR)
                # 检查ES中是否已存在
                need_update = True
                try:
                    es_doc = es.get(index=INDEX_NAME, id=rel_path)['_source']
                    # 比较本地文件和ES的更新时间
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(md_path))
                    es_time = datetime.strptime(es_doc['update_time'], '%Y-%m-%d %H:%M:%S')
                    if file_mtime <= es_time:
                        print(f'跳过未修改: {rel_path}')
                        need_update = False
                except Exception:
                    pass  # 不存在，直接导入
                if need_update:
                    doc = parse_and_copy(md_path)
                    es.index(index=INDEX_NAME, id=rel_path, body=doc)
                    print(f'导入/更新: {rel_path}')


if __name__ == '__main__':
    import_incremental()
