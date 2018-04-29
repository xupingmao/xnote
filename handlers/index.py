# encoding=utf-8
import web
import xtables
import xtemplate
import xauth
import xutils
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
    link("系统状态", "/system/monitor", "admin"),
    link("脚本管理", "/system/script", "admin"),
    link("定时任务",   "/system/crontab", "admin"),
    link("用户管理", "/system/user/list", "admin"),

    link("文件管理",   "/fs_data", "admin"),
    link("历史记录",   "/system/history", "admin"),
    link("App管理", "/system/app_admin", "admin"),
    link("后台模板缓存", "/system/template_cache", "admin"),
    link("重新加载模块", "/system/reload",         "admin"),
    link("Python文档", "/system/modules_info",    "admin"),

    link("标签云", "/file/taglist", "user"),
    link("词典", "/file/dict", "user"),
    link("备忘", "/message?status=created", "user"),
    link("最近更新", "/file/recent_edit", "user"),
    link("我的收藏", "/file/group/marked", "user"),

    # 无权限限制
    link("日历", "/tools/date"),
    link("代码模板", "/tools/code_template"),
    link("浏览器信息", "/tools/browser_info"),
    link("文本对比", "/tools/js_diff"),
    link("字符串转换", "/tools/string"),
    link("图片合并", "/tools/img_merge"),
    link("图片拆分", "/tools/img_split"),
    link("图像灰度化", "/tools/img2gray"),
    link("base64", "/tools/base64"),
    link("16进制转换", "/tools/hex"),
    link("md5", "/tools/md5"),
    link("sha1", "/tools/sha1"),
    link("URL编解码", "/tools/urlcoder"),
    link("二维码", "/tools/barcode"),
]


def tool_filter(item):
    if item.role is None:
        return True
    if xauth.get_current_role() == "admin":
        return True
    if xauth.get_current_role() == item.role:
        return True
    return False

class Home:

    def GET(self):
        sql = "SELECT * FROM file WHERE type = 'group' AND is_deleted = 0 AND creator = $creator ORDER BY name LIMIT 1000"
        data = list(xtables.get_file_table().query(sql, vars = dict(creator=xauth.get_current_name())))
        ungrouped_count = xtables.get_file_table().count(where="creator=$creator AND parent_id=0 AND is_deleted=0 AND type!='group'", 
            vars=dict(creator=xauth.get_current_name()))

        tools = list(filter(tool_filter, _tools))[:4]
        return xtemplate.render("index.html", 
            ungrouped_count = ungrouped_count,
            file_type="group_list",
            files = data,
            tools = tools)

class GridHandler:

    def GET(self):
        type = xutils.get_argument("type", "tool")
        items = []
        customized_items = []
        name = "工具库"
        if type == "tool":
            items = list(filter(tool_filter, _tools))
            db = xtables.get_config_table()
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

xurls = (
    r"/", Home, 
    r"/index", Home,
    r"/more", GridHandler,
    r"/unauthorized", Unauthorized,
    r"/favicon.ico", FaviconHandler
)

