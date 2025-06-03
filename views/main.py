import time
import os
import re
from flask import Blueprint, render_template, request, jsonify, current_app
from extensions import es, md

INDEX_NAME = 'wiki_docs'
PAGE_SIZE = 10

main_bp = Blueprint('main', __name__)


def search_docs(query, page=1, size=PAGE_SIZE):
    if query:
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content"],
                    "operator": "or",
                    "type": "best_fields"
                }
            },
            "from": (page - 1) * size,
            "size": size,
            "sort": [{"update_time": {"order": "desc"}}],
            "track_total_hits": True
        }
    else:
        body = {
            "query": {"match_all": {}},
            "from": (page - 1) * size,
            "size": size,
            "sort": [{"update_time": {"order": "desc"}}],
            "track_total_hits": True
        }
    res = es.search(index=INDEX_NAME, body=body)
    hits = res['hits']['hits']
    for hit in hits:
        if '_source' not in hit:
            hit['_source'] = {}
        if 'content' not in hit['_source']:
            hit['_source']['content'] = ''
        if 'title' not in hit['_source']:
            hit['_source']['title'] = 'Untitled'
        if 'update_time' not in hit['_source']:
            hit['_source']['update_time'] = ''
        if 'views' not in hit['_source']:
            hit['_source']['views'] = 0
    return hits, res['hits']['total']['value']


@main_bp.route('/')
def index():
    start = time.time()
    q = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    docs, total = search_docs(q, page)
    result = render_template('index.html',
                             docs=docs,
                             q=q,
                             page=page,
                             total=total,
                             max=max,
                             min=min,
                             PAGE_SIZE=PAGE_SIZE)
    return result


@main_bp.route('/doc/<id>')
def doc_detail(id):
    doc = es.get(index=INDEX_NAME, id=id)['_source']
    views = doc.get('views', 0) + 1
    es.update(
        index=INDEX_NAME,
        id=id,
        body={"doc": {"views": views}}
    )
    doc['views'] = views
    html = md.render(doc.get('content', ''))
    return render_template('detail.html', doc=doc, html=html, doc_id=id)


@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    from flask import current_app, abort, send_from_directory
    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(full_path):
        abort(404)
    dir_name = os.path.dirname(filename)
    file_name = os.path.basename(filename)
    return send_from_directory(os.path.join(current_app.config['UPLOAD_FOLDER'], dir_name), file_name)


@main_bp.route('/doc/<id>/delete', methods=['POST'])
def delete_doc(id):
    try:
        # 获取文档信息
        doc = es.get(index=INDEX_NAME, id=id)['_source']
        
        # 删除关联的图片文件
        content = doc.get('content', '')
        for img_url in re.findall(r'!\[.*?\]\(/uploads/images/([^)]+)\)', content):
            img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', img_url)
            if os.path.exists(img_path):
                os.remove(img_path)
        
        # 删除关联的附件
        if 'attachments' in doc:
            for attachment in doc['attachments']:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], attachment['url'].lstrip('/uploads/'))
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        # 删除 Elasticsearch 中的文档
        es.delete(index=INDEX_NAME, id=id)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/docs/batch-delete', methods=['POST'])
def batch_delete_docs():
    try:
        ids = request.json.get('ids', [])
        if not ids:
            return jsonify({'success': False, 'error': 'No documents specified'}), 400
        
        failed_ids = []
        for doc_id in ids:
            try:
                # 获取文档信息
                doc = es.get(index=INDEX_NAME, id=doc_id)['_source']
                
                # 删除关联的图片文件
                content = doc.get('content', '')
                for img_url in re.findall(r'!\[.*?\]\(/uploads/images/([^)]+)\)', content):
                    img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', img_url)
                    if os.path.exists(img_path):
                        os.remove(img_path)
                
                # 删除关联的附件
                if 'attachments' in doc:
                    for attachment in doc['attachments']:
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], attachment['url'].lstrip('/uploads/'))
                        if os.path.exists(file_path):
                            os.remove(file_path)
                
                # 删除 Elasticsearch 中的文档
                es.delete(index=INDEX_NAME, id=doc_id)
                
            except Exception:
                failed_ids.append(doc_id)
        
        if failed_ids:
            return jsonify({
                'success': True,
                'partial_failure': True,
                'failed_ids': failed_ids
            })
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/docs/delete-all', methods=['POST'])
def delete_all_docs():
    try:
        # 获取所有文档
        result = es.search(
            index=INDEX_NAME,
            body={
                "query": {"match_all": {}},
                "size": 10000  # 设置一个较大的值以获取所有文档
            }
        )
        
        total_docs = len(result['hits']['hits'])
        failed_count = 0
        
        # 删除每个文档
        for hit in result['hits']['hits']:
            try:
                doc_id = hit['_id']
                doc = hit['_source']
                
                # 删除关联的图片文件
                content = doc.get('content', '')
                for img_url in re.findall(r'!\[.*?\]\(/uploads/images/([^)]+)\)', content):
                    img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', img_url)
                    if os.path.exists(img_path):
                        os.remove(img_path)
                
                # 删除关联的附件
                if 'attachments' in doc:
                    for attachment in doc['attachments']:
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], attachment['url'].lstrip('/uploads/'))
                        if os.path.exists(file_path):
                            os.remove(file_path)
                
                # 删除 Elasticsearch 中的文档
                es.delete(index=INDEX_NAME, id=doc_id)
                
            except Exception:
                failed_count += 1
        
        return jsonify({
            'success': True,
            'total': total_docs,
            'failed': failed_count,
            'deleted': total_docs - failed_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500 