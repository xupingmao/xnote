# encoding=utf-8
import xtemplate

HTML = """
{% extends base %}

{% block body_left %}
    {% include common/layout/wide_left.html %}

    <div class="card">
        <p class="align-center">功能开发中</p>
        <p class="align-center">{%include common/button/back_button.html%}</p>
    </div>
{% end %}
"""

class TodoHandler:

    def GET(self):
        return xtemplate.render_text(HTML)

xurls = (
    r"/system/todo", TodoHandler,
)