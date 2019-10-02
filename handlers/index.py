# encoding=utf-8
# @author xupingmao
# @since 2017/02/19
# @modified 2019/10/02 14:35:53
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
from xutils import History

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

def link(name, link, role = None):
    return Storage(name = name, link = link, role = role)

def list_tools():
    tools = []
    for group in xconfig.MENU_LIST:
        for link in group.children:
            tools.append(link)
    return tools

def tool_filter(item):
    if item.role is None:
        return True
    if xauth.get_current_role() == "admin":
        return True
    if xauth.get_current_role() == item.role:
        return True
    return False

def list_most_visited():
    where = "is_deleted = 0 AND (creator = $creator OR is_public = 1)"
    db = xtables.get_file_table()
    return list(db.select(where = where, 
            vars   = dict(creator = xauth.get_current_name()),
            order  = "visited_cnt DESC",
            limit  = 5))

class IndexHandler:

    @xutils.timeit(name = "Home", logfile = True)
    def GET(self):
        if xauth.has_login():
            raise web.found("/note/books")
        else:
            raise web.found("/note/public")

        # 老的逻辑
        current_name  = xauth.current_name()
        groups        = xutils.call("note.list_group")
        notes         = xutils.call("note.list_recent_edit", limit = xconfig.RECENT_SIZE)
        tools         = list(filter(tool_filter, list_tools()))[:4]
        # tags        = xutils.call("note.list_tag", current_name)
        tags          = []
        recent_search = xutils.call("search.list_recent", current_name, xconfig.RECENT_SEARCH_LIMIT)
        return xtemplate.render("index.html", 
            file_type       = "home",
            show_aside      = True,
            recent_search   = recent_search,
            groups          = groups,
            notes           = notes,
            files           = groups,
            tags            = tags,
            tools           = tools)

class GridHandler:

    def GET(self):
        type             = xutils.get_argument("type", "tool")
        items            = []
        customized_items = []
        name             = "工具库"
        if type == "tool":
            items  = list(filter(tool_filter, list_tools()))
            db     = xtables.get_storage_table()
            config = db.select_first(where=dict(key="tools", user=xauth.get_current_name()))
            if config is not None:
                config_list = xutils.parse_config_text(config.value)
                customized_items = map(lambda x: Storage(name=x.get("key"), link=x.get("value")), config_list)
        return xtemplate.render("grid.html", items=items, name = name, customized_items = customized_items)

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
    r"/home", IndexHandler,
    r"/more", GridHandler,
    r"/unauthorized", Unauthorized,
    r"/favicon.ico", FaviconHandler
)

