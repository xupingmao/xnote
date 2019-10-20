# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/10
# @modified 2019/10/20 18:29:11
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

def link(name, url, user = None, icon = "cube"):
    return Storage(name = name, url = url, link = url, user = user, icon = icon)

def admin_link(name, url, icon = "cube"):
    return link(name, url, "admin", icon)

def user_link(name, url, icon = "cube"):
    return link(name, url, None, icon)

SYS_TOOLS = [
    admin_link("Menu_Settings",   "/system/settings", "cog"),
    admin_link("Menu_File",       "/fs_list", "file"),
    admin_link("Menu_Scripts",    "/fs_link/scripts"),
    admin_link("Menu_Cron",   "/system/crontab"),
    admin_link("Menu_User",   "/system/user/list", "users"),
    admin_link("Menu_Log",    "/system/log"),
    admin_link("Menu_Refresh",  "/system/reload", "refresh"),
    admin_link("Menu_Modules",  "/system/modules_info"),
    admin_link("Menu_Configure", "/code/edit?type=script&path=" + str(xconfig.INIT_SCRIPT)),
    admin_link("Menu_CSS", "/code/edit?type=script&path=user.css"),
    admin_link("Menu_Plugin",   "/plugins_list"),
    admin_link("Shell",    "/tools/shell")
] 

NOTE_TOOLS = [
    user_link("Search History",      "/search"),

    # 笔记
    user_link("Recent Updated",      "/note/recent_edit", "folder"),
    user_link("Recent Created",      "/note/recent_created", "folder"),
    user_link("Recent Viewed",       "/note/recent_viewed", "folder"),
    user_link("默认分类", "/note/default", "folder"),
    user_link("笔记本", "/note/group", "book"),
    user_link("书架", "/note/category", "book"),
    user_link("标签列表", "/note/taglist", "tags"),
    user_link("时光轴", "/note/tools/timeline"),
    user_link("字典", "/note/dict"),

    # 提醒
    user_link("待办",  "/message?status=created", "calendar-check-o"),
    user_link("日历", "/message/calendar", "calendar"),
    user_link("上传管理", "/fs_upload", "upload"),
    user_link("数据统计", "/note/stat", "bar-chart"),
] 

DATA_TOOLS = [
    admin_link("数据迁移",  "/system/db_migrate", "database"),
    admin_link("SQL", "/tools/sql", "database"),
    admin_link("leveldb", "/system/db_scan", "database")
]

OTHER_TOOLS = [
    link("浏览器信息", "/tools/browser_info"),
    # 文本
    user_link("代码模板", "/tools/code_template", "code"),
    user_link("文本对比", "/tools/js_diff", "code"),
    user_link("文本转换", "/tools/text_processor", "code"),
    user_link("随机字符串", "/tools/random_string", "code"),
    # 图片
    user_link("图片合并", "/tools/img_merge", "image"),
    user_link("图片拆分", "/tools/img_split", "image"),
    user_link("图像灰度化", "/tools/img2gray", "image"),
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
    Storage(name = "System", children = SYS_TOOLS, need_login = True),
    Storage(name = "Note", children = NOTE_TOOLS, need_login = True),
    Storage(name = "数据管理", children = DATA_TOOLS, need_login = True),
    Storage(name = "Tools", children = OTHER_TOOLS),
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
        return xtemplate.render("system/template/system.html", 
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
        import web
        autoreload.reload()
        raise web.seeother("/system/settings")

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
    r"/system/user\.css", UserCssHandler,
    r"/system/user\.js", UserJsHandler,
    r"/system/cache", CacheHandler
)
