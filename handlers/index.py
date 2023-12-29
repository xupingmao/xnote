# encoding=utf-8
# @author xupingmao
# @since 2017/02/19
# @modified 2021/05/23 19:33:48
import web
from xnote.core import xtemplate
from xnote.core import xauth
import xutils

INDEX_HTML = """
{% extends base %}
{% block body %}
    <h1 style="text-align:center;">Welcome to Xnote!</h1>
{% end %}
"""

UNAUTHORIZED_HTML = """
{% extends base %}
{% block body %}
    <div class="card">
        <div class="card-title">
            <span>无访问权限</span>
            <div class="float-right">
                {% include common/button/back_button.html %}
            </div>
        </div>
    </div>

    <div class="card">
        <h3>抱歉,您没有访问的权限</h3>
    </div>
{% end %}

{% block body_right %}
    {% include common/sidebar/default.html %}
{% end %}
"""


class IndexHandler:

    @xutils.timeit(name = "Home", logfile = True)
    def GET(self):
        if xauth.has_login():
            user_name = xauth.current_name()
            raise web.found("/note/index")
        else:
            raise web.found("/note/public")

class Unauthorized():
    def GET(self):
        web.ctx.status = "401 Unauthorized"
        return xtemplate.render_text(UNAUTHORIZED_HTML)

class FaviconHandler:

    def GET(self):
        raise web.found("/static/favicon.ico")

xurls = (
    r"/", IndexHandler,
    r"/index", IndexHandler,
    r"/home",  IndexHandler,
    r"/unauthorized", Unauthorized,
    r"/favicon.ico", FaviconHandler
)

