# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/10
# @modified 2019/04/17 01:00:55
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
    admin_link("Menu_Plugin",   "/plugins_list"),
    admin_link("Shell",    "/tools/shell")
] 

doc_tools = [
    link("Search History",      "/search"),

    # 笔记
    link("Recent Updated",      "/note/recent_edit"),
    link("Recent Created",      "/note/recent_created"),
    link("Recent Viewed",       "/note/recent_viewed"),
    link("Note Groups",         "/note/group"),
    link("Note Tags",           "/note/taglist"),
    link("Uncategorized Notes", "/note/ungrouped"),
    link("Timeline", "/tools/timeline"),
    link("Dictionary",          "/note/dict"),

    # 提醒
    link("Message",  "/message?status=created"),
    link("Calendar", "/message/calendar"),
] 

other_tools = [
    link("浏览器信息", "/tools/browser_info"),
    # 文本
    link("代码模板", "/tools/code_template"),
    link("文本对比", "/tools/js_diff"),
    link("文本转换", "/tools/text_processor"),
    link("随机字符串", "/tools/random_string"),
    # 图片
    link("图片合并", "/tools/img_merge"),
    link("图片拆分", "/tools/img_split"),
    link("图像灰度化", "/tools/img2gray"),
    # 编解码
    link("base64", "/tools/base64"),
    link("HEX转换", "/tools/hex"),
    link("md5签名", "/tools/md5"),
    link("sha1签名", "/tools/sha1"),
    link("URL编解码", "/tools/urlcoder"),
    link("条形码", "/tools/barcode"),
    link("二维码", "/tools/qrcode"),
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
    Storage(name = "File", url = "/fs_upload", user = "*"),
    Storage(name = "Tool", url = "/plugins_list", user = "admin"),
]

xconfig.NOTE_OPTIONS = [
    link("New_Note", "/note/add"),
    link("Recent Updated", "/note/recent_edit"),
    link("Recent Created", "/note/recent_created"),
    link("Recent View",  "/note/recent_viewed"),
    link("Public",   "/note/public"),
    link("Tag List", "/note/taglist"),
]

@xutils.cache(expire=60)
def get_tools_config(user):
    db  = xtables.get_storage_table()
    user_config = db.select_first(where=dict(key="tools", user=user))
    return user_config

                
class IndexHandler:

    def GET(self):
        # 自定义链接
        # customized_items = []
        # user_config = get_tools_config(xauth.get_current_name())
        # if user_config is not None:
        #     config_list = xutils.parse_config_text(user_config.value)
        #     customized_items = map(lambda x: Storage(name=x.get("key"), url=x.get("value")), config_list)

        return xtemplate.render("system/system.html", 
            show_aside       = (xconfig.OPTION_STYLE == "aside"),
            html_title       = "系统",
            Storage          = Storage,
            os               = os,
            user             = xauth.get_current_user(),
            customized_items = []
        )


class ReloadHandler:
    @xauth.login_required("admin")
    def GET(self):
        # autoreload will load new handlers
        import autoreload
        autoreload.reload()
        import web
        raise web.seeother("/system/settings")


class ConfigHandler:

    @xauth.login_required("admin")
    def POST(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")

        if key == "BASE_TEMPLATE":
            xmanager.reload()
        if key in ("FS_HIDE_FILES", "DEBUG_HTML_BOX"):
            value = value.lower() in ("true", "yes", "on")
        if key == "DEBUG":
            setattr(xconfig, key, value == "True")
            web.config.debug = xconfig.DEBUG
        if key in ("RECENT_SEARCH_LIMIT", "RECENT_SIZE", "PAGE_SIZE"):
            value = int(value)
        if key == "LANG":
            web.setcookie("lang", value)

        setattr(xconfig, key, value)
        cacheutil.hset('sys.config', key, value)
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
    for key in ('THEME', 'FS_HIDE_FILES', 'OPTION_STYLE', 'PAGE_OPEN', 'RECENT_SEARCH_LIMIT', "PAGE_SIZE", "RECENT_SIZE"):
        value = cacheutil.hget('sys.config', key)
        xutils.trace("HGET", "key=%s, value=%s" % (key, value))
        if value is not None:
            setattr(xconfig, key, value)

    path = os.path.join(xconfig.SCRIPTS_DIR, "user.css")
    if not os.path.exists(path):
        return 
    xconfig.set("USER_CSS", xutils.readfile(path))
