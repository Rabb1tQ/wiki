from elasticsearch import Elasticsearch
from markdown_it import MarkdownIt


def custom_render_fence(tokens, idx, options, env):
    token = tokens[idx]
    lang = token.info.strip() if token.info else ''
    code = token.content
    if lang:
        return f'<pre class="line-numbers"><code class="language-{lang}">{code}</code></pre>'
    return f'<pre class="line-numbers"><code class="language-plaintext">{code}</code></pre>'


es = Elasticsearch(
    ['http://192.168.239.136:9200'],
    http_auth=('elastic', 'changeme')
)

md = (MarkdownIt('commonmark', {'breaks': True, 'html': True})
      .enable('table')
      .enable('strikethrough')
      .enable('linkify'))
md.renderer.rules['fence'] = custom_render_fence
