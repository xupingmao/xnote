#encoding=utf-8
import web
import os

from web import xtemplate
from xutils import *

# 这里也是提供一个render_text的示例
# 文本直接读入的时候，他的路径是template的根目录,也就是model
html = """
{% extends base.html %}
{% block body %}

<form method="POST">
<input class="hide" name="type" value="{{type}}"/>
<input class="hide" name="target" value="{{target}}"/>
<div>
    {% if type == "file" %} 文件名 {% else %} 目录名 {% end %}
    <input type="text" name="name" />
    <br/>
    <button>确定</button>
    <br/>
    <font color="red">{{error}}</font>
</div>
</form>

{% end %}
"""


WIKI_PATH = "static/wiki/"

class handler:
    
    def GET(self):
        type = web.input(type="file").type
        target = web.input().target
        return xtemplate.render_text(html, type = type, target = target, error="")

    def POST(self):
        params = web.input()
        name = params.name
        type = params.type
        target = params.target
        if not name.endswith(".md"):
            name+=".md"
        path = os.path.join(WIKI_PATH, target, name)
        if os.path.exists(path):
            return xtemplate.render_text(html, type=type, target=target, error="文件已存在")
        if type == "file":
            open(path, "wb").close()
        else:
            # dir
            path = os.makedirs(path)
        raise web.seeother("/wiki/" + quote(target))