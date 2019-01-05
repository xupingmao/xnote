# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/10
# @modified 2019/01/05 13:15:50
"""System functions"""
from io import StringIO
import xconfig
import codecs
import time
import functools
import os
import json
import socket
import os
import autoreload
import xtemplate
import xutils
import xauth
import xmanager
import xtables
import web
from xtemplate import BasePlugin
from xutils import History
from xutils import cacheutil
from xutils import Storage
from xtemplate import T

def link(name, url, user = None):
    return Storage(name = name, url = url, link = url, user = user)

def admin_link(name, url):
    return link(name, url, "admin")

sys_tools = [
    admin_link("Menu_Settings",   "/system/settings"),
    admin_link("Menu_Configure",  "/code/edit?type=script&path=" + str(xconfig.INIT_SCRIPT)),
    admin_link("Menu_File",       "/fs_list"),
    admin_link("Menu_Scripts",    "/fs_link/scripts"),
    admin_link("Menu_Cron",   "/system/crontab"),
    admin_link("Menu_User",   "/system/user/list"),
    admin_link("Menu_Log",    "/system/history"),
    admin_link("Menu_Refresh",  "/system/reload"),
    admin_link("Menu_Modules",  "/system/modules_info"),
    admin_link("SQL",      "/tools/sql"),
    admin_link("Menu_CSS", "/code/edit?type=script&path=user.css"),
    admin_link("Plugin",   "/plugins_list"),
    admin_link("Shell",    "/tools/shell"),
    link("About System",    "/code/wiki/README.md"),
] 

doc_tools = [
    link("Search History",      "/search"),
    link("Recent Updated",      "/note/recent_edit"),
    link("Recent Created",      "/note/recent_created"),
    link("Note Categories",     "/note/group"),
    link("Note Tags",           "/note/taglist"),
    link("Uncategorized Notes", "/note/ungrouped"),
    link("Dictionary",          "/note/dict"),
    link("Message",  "/message?status=created"),
    link("Calendar", "/message/calendar"),
    link("Timeline", "/tools/timeline"),
] 

other_tools = [
    link("代码模板", "/tools/code_template"),
    link("浏览器信息", "/tools/browser_info"),
    link("文本对比", "/tools/js_diff"),
    link("文本转换", "/tools/text_processor"),
    link("图片合并", "/tools/img_merge"),
    link("图片拆分", "/tools/img_split"),
    link("图像灰度化", "/tools/img2gray"),
    link("base64", "/tools/base64"),
    link("16进制转换", "/tools/hex"),
    link("md5签名", "/tools/md5"),
    link("sha1签名", "/tools/sha1"),
    link("URL编解码", "/tools/urlcoder"),
    link("条形码生成", "/tools/barcode"),
    link("二维码生成", "/tools/qrcode"),
    link("随机生成器", "/tools/random_string"),
    # 其他工具
    link("分屏模式", "/tools/multi_win"),
    link("RunJS", "/tools/runjs"),
]

# 所有功能配置
xconfig.MENU_LIST = [
    Storage(name = "System", children = sys_tools, need_login = True),
    Storage(name = "Data", children = doc_tools, need_login = True),
    Storage(name = "Tools", children = other_tools),
]

# 导航配置
xconfig.NAV_LIST = [
    Storage(name = "Plugin", url = "/plugins_list", user = "admin"),
    Storage(name = "About",   url = "/code/wiki/README.md"),
]

xconfig.NOTE_OPTIONS = [
    link("New_Note", "/note/add"),
    link("Recent Updated", "/note/recent_created"),
    link("Recent Created", "/note/recent_created"),
    link("Public",   "/note/public"),
    link("Tag List", "/note/taglist"),
]

@xutils.cache(expire=60)
def get_tools_config(user):
    db  = xtables.get_storage_table()
    user_config = db.select_one(where=dict(key="tools", user=user))
    return user_config

                
class IndexHandler:

    def GET(self):
        shell_list = []
        dirname = "scripts"
        if os.path.exists(dirname):
            for fname in os.listdir(dirname):
                fpath = os.path.join(dirname, fname)
                if os.path.isfile(fpath) and fpath.endswith(".bat"):
                    shell_list.append(fpath)

        # 自定义链接
        customized_items = []
        user_config = get_tools_config(xauth.get_current_name())
        if user_config is not None:
            config_list = xutils.parse_config_text(user_config.value)
            customized_items = map(lambda x: Storage(name=x.get("key"), url=x.get("value")), config_list)

        return xtemplate.render("system/system.html", 
            show_aside       = (xconfig.OPTION_STYLE == "aside"),
            html_title       = "系统",
            Storage          = Storage,
            os               = os,
            user             = xauth.get_current_user(),
            customized_items = customized_items
        )


class ReloadHandler:
    @xauth.login_required("admin")
    def GET(self):
        xmanager.reload()
        import web
        raise web.seeother("/system/index")


class ConfigHandler:

    @xauth.login_required("admin")
    def POST(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")
        setattr(xconfig, key, value)
        cacheutil.hset('sys.config', key, value)

        if key == "BASE_TEMPLATE":
            xmanager.reload()
        if key == "FS_HIDE_FILES":
            setattr(xconfig, key, value == "True")
        if key == "DEBUG":
            setattr(xconfig, key, value == "True")
            web.config.debug = xconfig.DEBUG
        if key == "LANG":
            web.setcookie("lang", value)
        return dict(code="success")

class UserCssHandler:

    def GET(self):
        web.header("Content-Type", "text/css")
        environ = web.ctx.environ
        path = os.path.join(xconfig.SCRIPTS_DIR, "user.css")

        if not xconfig.DEBUG:
            web.header("Cache-Control", "max-age=3600")

        if not os.path.exists(path):
            return b''
        
        etag = '"%s"' % os.path.getmtime(path)
        client_etag = environ.get('HTTP_IF_NONE_MATCH')
        web.header("Etag", etag)
        if etag == client_etag:
            web.ctx.status = "304 Not Modified"
            return b'' # 其实webpy已经通过yield空bytes来避免None
        return xutils.readfile(path)
        # return xconfig.get("USER_CSS", "")

class UserJsHandler:

    def GET(self):
        web.header("Content-Type", "application/javascript")
        return xconfig.get("USRE_JS", "")
        
class CacheHandler:

    @xauth.login_required("admin")
    def POST(self):
        key = xutils.get_argument("key", "")
        value = xutils.get_argument("value", "")
        cacheutil.set(key, value)
        return dict(code = "success")

    @xauth.login_required("admin")
    def GET(self):
        key = xutils.get_argument("key", "")
        return dict(code = "success", data = cacheutil.get(key))

xurls = (
    r"/system/sys",   IndexHandler,
    r"/system/index", IndexHandler,
    r"/system/system", IndexHandler,
    r"/system/reload", ReloadHandler,
    r"/system/config", ConfigHandler,
    r"/system/user\.css", UserCssHandler,
    r"/system/user\.js", UserJsHandler,
    r"/system/cache", CacheHandler
)

@xmanager.listen("sys.reload")
def on_reload(ctx = None):
    for key in ('THEME', 'FS_HIDE_FILES', 'OPTION_STYLE', 'PAGE_OPEN'):
        value = cacheutil.hget('sys.config', key)
        xutils.log("hget key=%s, value=%s" % (key, value))
        if value is not None:
            setattr(xconfig, key, value)

    path = os.path.join(xconfig.SCRIPTS_DIR, "user.css")
    if not os.path.exists(path):
        return 
    xconfig.set("USER_CSS", xutils.readfile(path))
