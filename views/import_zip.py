import os
import re
import uuid
import time
import tempfile
import shutil
import chardet
from zipfile import ZipFile
from flask import Blueprint, render_template, request, current_app
from extensions import es

INDEX_NAME = 'wiki_docs'

import_zip_bp = Blueprint('import_zip', __name__)


def detect_encoding(file_path):
    """
    检测文件编码
    """
    with open(file_path, 'rb') as f:
        raw = f.read()
        result = chardet.detect(raw)
        return result['encoding'] or 'utf-8'


def extract_title(content, md_path):
    """
    提取文档标题，优先级：
    1. markdown文件中的第一个#标题
    2. 如果是index.md则使用上级目录名
    3. 使用文件名（不含扩展名）
    """
    # 优先用markdown第一行#标题作为title
    for line in content.splitlines():
        m = re.match(r'^#\s+(.+)', line.strip())
        if m:
            return m.group(1)
    
    # 如果是index.md则用上级目录名
    basename = os.path.basename(md_path).lower()
    if basename == 'index.md':
        dirname = os.path.basename(os.path.dirname(md_path))
        try:
            # 尝试使用gbk解码
            dirname = dirname.encode('cp437').decode('gbk')
        except:
            try:
                # 如果gbk失败，尝试utf-8
                dirname = dirname.encode('cp437').decode('utf-8')
            except:
                pass
        return dirname
    
    # 否则用文件名
    filename = os.path.splitext(os.path.basename(md_path))[0]
    try:
        # 尝试使用gbk解码
        filename = filename.encode('cp437').decode('gbk')
    except:
        try:
            # 如果gbk失败，尝试utf-8
            filename = filename.encode('cp437').decode('utf-8')
        except:
            pass
    return filename


@import_zip_bp.route('/import_zip', methods=['GET', 'POST'])
def import_zip():
    message = ''
    if request.method == 'POST':
        zip_file = request.files.get('zipfile')
        if not zip_file or not zip_file.filename.endswith('.zip'):
            message = '请上传zip文件！'
            return render_template('import_zip.html', message=message)
        
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, zip_file.filename)
        zip_file.save(zip_path)
        
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)
        
        imported = 0
        IMAGE_FOLDER = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images')
        ATTACH_FOLDER = os.path.join(current_app.config['UPLOAD_FOLDER'], 'attachments')
        
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                if file.endswith('.md'):
                    md_path = os.path.join(root, file)
                    # 检测文件编码
                    encoding = detect_encoding(md_path)
                    try:
                        with open(md_path, 'r', encoding=encoding) as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        # 如果检测到的编码不正确，尝试使用 utf-8
                        with open(md_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                    def repl_img_att(match):
                        orig_path = match.group(2)
                        abs_path = os.path.normpath(os.path.join(os.path.dirname(md_path), orig_path))
                        if os.path.exists(abs_path):
                            ext = os.path.splitext(abs_path)[1]
                            uuid_name = f"{uuid.uuid4().hex}{ext}"
                            if ext.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']:
                                dest = os.path.join(IMAGE_FOLDER, uuid_name)
                                url = f"/uploads/images/{uuid_name}"
                                shutil.copyfile(abs_path, dest)
                            else:
                                dest = os.path.join(ATTACH_FOLDER, uuid_name)
                                url = f"/uploads/attachments/{uuid_name}"
                                shutil.copyfile(abs_path, dest)
                            return f"{match.group(1)}({url})"
                        return match.group(0)

                    content = re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)', repl_img_att, content)
                    
                    # 使用新的标题提取逻辑
                    title = extract_title(content, md_path)
                    
                    attachments = []
                    for m in re.finditer(r'\[[^\]]+\]\((/uploads/attachments/[^)]+)\)', content):
                        url = m.group(1)
                        name = os.path.basename(url)
                        attachments.append({'name': name, 'url': url})
                    
                    rel_path = os.path.relpath(md_path, tmp_dir)
                    try:
                        # 尝试转换路径编码
                        category = os.path.dirname(rel_path).encode('cp437').decode('gbk')
                    except:
                        try:
                            category = os.path.dirname(rel_path).encode('cp437').decode('utf-8')
                        except:
                            category = os.path.dirname(rel_path)
                    
                    doc = {
                        'title': title,
                        'content': content,
                        'attachments': attachments,
                        'category': category,
                        'update_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'views': 0
                    }
                    es.index(index=INDEX_NAME, id=rel_path, body=doc)
                    imported += 1
        
        shutil.rmtree(tmp_dir)
        message = f'成功导入 {imported} 个markdown文档！'
    
    return render_template('import_zip.html', message=message)
