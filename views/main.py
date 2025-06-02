import time
from flask import Blueprint, render_template, request
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
    return render_template('detail.html', doc=doc, html=html)


@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    import os
    from flask import current_app, abort, send_from_directory
    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(full_path):
        abort(404)
    dir_name = os.path.dirname(filename)
    file_name = os.path.basename(filename)
    return send_from_directory(os.path.join(current_app.config['UPLOAD_FOLDER'], dir_name), file_name) 