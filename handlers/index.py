# encoding=utf-8
from handlers.base import *
from handlers.file import dao

index_html = """{% extends base.html %}
{% block body %}
<h1 style="text-align:center;">Welcome to Xnote!</h1>
{% end %}
"""

searchable = False

class Home:

    def GET(self):
        return xtemplate.render("search_result.html", files = [])
        # raise web.seeother("/file/recent_edit")
        # return xtemplate.render_text(index_html)

class Unauthorized():
    html = """
{% extends base.html %}
{% block body %}
    <h3>抱歉,您没有访问的权限</h3>
{% end %}
    """
    def GET(self):
        web.ctx.status = "401 Unauthorized"
        return xtemplate.render_text(self.html)

xurls = (
    r"/", Home, 
    r"/index", Home,
    r"/unauthorized", Unauthorized
)

