# encoding=utf-8
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

index_html = """
{% extends base.html %}
{% block body %}
<h1 style="text-align:center;">Welcome to Xnote!</h1>
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

    def GET(self):
        t = Timer()
        t.start()
        sql  = "SELECT * FROM file WHERE type = 'group' AND is_deleted = 0 AND creator = $creator ORDER BY name LIMIT 1000"
        data = list(xtables.get_file_table().query(sql, vars = dict(creator=xauth.get_current_name())))
        t.stop()
        xutils.log("group time: %s" % t.cost())

        t.start()
        ungrouped_count = xtables.get_file_table().count(where="creator=$creator AND parent_id=0 AND is_deleted=0 AND type!='group'", 
            vars=dict(creator=xauth.get_current_name()))
        t.stop()
        xutils.log("recent time: %s" % t.cost())

        tools = list(filter(tool_filter, list_tools()))[:4]
        return xtemplate.render("index.html", 
            ungrouped_count = ungrouped_count,
            file_type       = "group_list",
            files           = data,
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
            config = db.select_one(where=dict(key="tools", user=xauth.get_current_name()))
            if config is not None:
                config_list = xutils.parse_config_text(config.value)
                customized_items = map(lambda x: Storage(name=x.get("key"), link=x.get("value")), config_list)
        return xtemplate.render("grid.html", items=items, name = name, customized_items = customized_items)

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

class FaviconHandler:

    def GET(self):
        raise web.seeother("/static/favicon.ico")

class PluginsHandler:

    def GET(self, name = ""):
        display_name = xutils.unquote(name)
        name = xutils.get_real_path(display_name)
        if not name.endswith(".py"):
            name += ".py"
        script_name = "plugins/" + name
        if not os.path.exists(os.path.join(xconfig.PLUGINS_DIR, name)):
            error = "file `%s` not found" % script_name
            return xtemplate.render("error.html", error=error)
        try:
            try:
                cacheutil.zadd("plugins.history", time.time(), os.path.splitext(display_name)[0])
            except TypeError:
                cacheutil.delete("plugins.history")
                cacheutil.zadd("plugins.history", time.time(), os.path.splitext(display_name)[0])
            vars = dict()
            vars["script_name"] = script_name
            xutils.load_script(script_name, vars)
            main_class = vars.get("Main")
            if main_class != None:
                return main_class().render()
            else:
                return xtemplate.render("error.html", error="class `Main` not found!")
        except:
            error = xutils.print_exc()
            return xtemplate.render("error.html", error=error)

    def POST(self, name = ""):
        return self.GET(name)

xurls = (
    r"/", "handlers.note.group.RecentEditHandler", 
    r"/index", IndexHandler,
    r"/home", IndexHandler,
    r"/more", GridHandler,
    # r"/system/index", GridHandler,
    r"/unauthorized", Unauthorized,
    r"/favicon.ico", FaviconHandler,
    r"/plugins/(.+)", PluginsHandler
)

