# -*- coding:utf-8 -*-  
# Created by xupingmao on 2016/10
# @modified 2018/10/10 00:29:51

"""Description here"""
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
config = xconfig

def link(name, url):
    return Storage(name = name, url = url, link = url)

sys_tools = [
    link("系统状态",   "/system/monitor"),
    link("文件管理",   "/fs_list"),
    link("脚本管理",   "/fs_link/scripts"),
    link("定时任务",   "/system/crontab"),
    link("访问记录",   "/system/history"),
    link("用户管理",   "/system/user/list"),
    link("App管理",   "/fs_link/app"),
    # link("后台模板缓存", "/system/template_cache"),
    link("系统刷新",  "/system/reload"),
    link("Python文档", "/system/modules_info"),
    link("SQL控制台", "/tools/sql"),
    link("启动规则", "/code/edit?type=script&path=" + str(xconfig.INIT_SCRIPT)),
    link("定制CSS", "/code/edit?type=script&path=user.css")
] 

doc_tools = [
    link("搜索", "/search"),
    link("分类", "/note/group"),
    link("未分类", "/note/ungrouped"),
    link("标签", "/note/taglist"),
    link("词典", "/file/dict"),
    link("提醒", "/message?status=created"),
    link("最近", "/file/recent_edit"),
    link("日历", "/message/calendar"),
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
    link("md5", "/tools/md5"),
    link("sha1签名", "/tools/sha1"),
    link("URL编解码", "/tools/urlcoder"),
    link("条形码", "/tools/barcode"),
    link("二维码", "/tools/qrcode"),
    link("随机生成器", "/tools/random_string"),
    # 其他工具
    link("分屏模式", "/tools/command_center")
]

xconfig.MENU_LIST = [
    Storage(name = "系统管理", children = sys_tools, need_login = True, need_admin = True),
    Storage(name = "知识库", children = doc_tools, need_login = True),
    Storage(name = "工具箱", children = other_tools),
]

                
class SysHandler:

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
        db  = xtables.get_storage_table()
        config = db.select_one(where=dict(key="tools", user=xauth.get_current_name()))
        if config is not None:
            config_list = xutils.parse_config_text(config.value)
            customized_items = map(lambda x: Storage(name=x.get("key"), link=x.get("value")), config_list)

        return xtemplate.render("system/system.html", 
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
        raise web.seeother("/")


class ConfigHandler:

    @xauth.login_required("admin")
    def POST(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")
        setattr(xconfig, key, value)
        if key == "BASE_TEMPLATE":
            xmanager.reload()
        if key == "FS_HIDE_FILES":
            setattr(xconfig, key, value == "True")
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
    r"/system/sys",   SysHandler,
    r"/system/index", SysHandler,
    r"/system/system", SysHandler,
    r"/system/reload", ReloadHandler,
    r"/system/xconfig", ConfigHandler,
    r"/system/user.css", UserCssHandler,
    r"/system/user.js", UserJsHandler,
    r"/system/cache", CacheHandler
)

