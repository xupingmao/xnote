# encoding=utf-8
import web
import xtables
import xtemplate
import xauth
import xutils
import os
import xconfig
from xutils import Storage

index_html = """
{% extends base.html %}
{% block body %}
<h1 style="text-align:center;">Welcome to Xnote!</h1>
{% end %}
"""

def link(name, link, role = None):
    return Storage(name = name, link = link, role = role)

_tools = [
    link("我的账号", "/system/user"),
    link("登出", "/logout", "user"),
    link("系统状态", "/system/monitor", "admin"),
    link("脚本管理", "/system/script", "admin"),
    link("定时任务",   "/system/crontab", "admin"),
    link("用户管理", "/system/user/list", "admin"),

    link("文件管理",   "/fs_data", "admin"),
    link("App管理",   "/fs_api/app", "admin"),
    link("历史记录",   "/system/history", "admin"),
    link("后台模板缓存", "/system/template_cache", "admin"),
    link("系统模块刷新", "/system/reload",         "admin"),
    link("Python文档", "/system/modules_info",    "admin"),

    link("旧版首页", "/index", "user"),
    link("标签云", "/file/taglist", "user"),
    link("词典", "/file/dict", "user"),
    link("备忘", "/message?status=created", "user"),
    link("最近更新", "/file/recent_edit", "user"),

    # 无权限限制
    link("日历", "/tools/date"),
    link("代码模板", "/tools/code_template"),
    link("浏览器信息", "/tools/browser_info"),
    link("我的IP", "/api/getip"),

    # 字符串工具
    link("文本对比", "/tools/js_diff"),
    link("字符串转换", "/tools/string"),

    # 图片处理工具
    link("图片合并", "/tools/img_merge"),
    link("图片拆分", "/tools/img_split"),
    link("图像灰度化", "/tools/img2gray"),

    # 编解码工具
    link("base64", "/tools/base64"),
    link("16进制转换", "/tools/hex"),
    link("md5", "/tools/md5"),
    link("sha1签名", "/tools/sha1"),
    link("URL编解码", "/tools/urlcoder"),
    link("条形码", "/tools/barcode"),
    link("二维码", "/tools/qrcode"),

    # 其他工具
    link("分屏", "/tools/command_center"),
    link("命令模式", "/fs_api/plugins?show_menu=true"),
]


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
        sql  = "SELECT * FROM file WHERE type = 'group' AND is_deleted = 0 AND creator = $creator ORDER BY name LIMIT 1000"
        data = list(xtables.get_file_table().query(sql, vars = dict(creator=xauth.get_current_name())))
        ungrouped_count = xtables.get_file_table().count(where="creator=$creator AND parent_id=0 AND is_deleted=0 AND type!='group'", 
            vars=dict(creator=xauth.get_current_name()))

        tools = list(filter(tool_filter, _tools))[:4]
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
            items  = list(filter(tool_filter, _tools))
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

class PageHandler:

    def GET(self, name = ""):
        if not name.endswith(".py"):
            name += ".py"
        script_name = "pages/" + name
        if not os.path.exists(os.path.join(xconfig.PAGES_DIR, name)):
            return "file `%s` not found" % script_name
        vars = dict()
        xutils.load_script(script_name, vars)
        main_func = vars.get("main")
        if main_func != None:
            return main_func()
        else:
            return "function `main` not found!"

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
    r"/pages/(.+)", PageHandler
)

