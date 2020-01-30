# encoding=utf-8
# @author xupingmao
# @since 2017/02/19
# @modified 2020/01/30 16:15:28
import web
import xtables
import xtemplate
import xauth
import xutils
import os
import xconfig
import time
from xutils import Storage, cacheutil
from xutils.dateutil import Timer

INDEX_HTML = """
{% extends base.html %}
{% block body %}
    <h1 style="text-align:center;">Welcome to Xnote!</h1>
{% end %}
"""

UNAUTHORIZED_HTML = """
{% extends base.html %}
{% block body %}
    <div class="box">
        <h3>抱歉,您没有访问的权限</h3>
    </div>
{% end %}
"""


class IndexHandler:

    @xutils.timeit(name = "Home", logfile = True)
    def GET(self):
        if xauth.has_login():
            user_name = xauth.current_name()
            raise web.found(xconfig.get_user_config(user_name, "HOME_PATH"))
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

