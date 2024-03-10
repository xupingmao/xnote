# -*- coding:utf-8 -*-
# Created by xupingmao on 2016/10
# @modified 2022/02/26 11:27:37
"""System functions"""
import os
from xnote.core import xconfig
from xnote.core import xtemplate
import xutils
from xnote.core import xauth
from xnote.core import xmanager
import web
from xutils import Storage
from xutils import webutil


class AppLink:
    def __init__(self):
        self.name = ""
        self.url = ""
        self.user = ""
        self.is_admin = False
        self.is_user = False
        self.is_guest = False
        self.is_public = False
        self.icon = None  # type: str|None
        self.img_src = None

    def build(self):
        self.url = xconfig.WebConfig.server_home + self.url
        if self.img_src != None:
            self.img_src = xconfig.WebConfig.server_home + self.img_src


def link(name, url, user="", icon="cube"):
    result = AppLink()
    result.name = name
    result.url = url
    result.user = user
    result.icon = icon
    result.build()
    return result


def admin_link(name, url, icon="cube"):
    link = AppLink()
    link.name = name
    link.url = url
    link.icon = icon
    link.is_admin = True
    link.user = "admin"
    link.build()
    return link


def user_link(name, url, icon="cube", img_src=None):
    link = AppLink()
    link.name = name
    link.url = url
    link.icon = icon
    link.img_src = img_src
    link.is_user = True
    link.build()
    return link


def guest_link(name, url, icon="cube"):
    link = AppLink()
    link.name = name
    link.url = url
    link.icon = icon
    link.is_guest = True
    link.build()
    return link


def public_link(name, url, icon="cube"):
    link = AppLink()
    link.name = name
    link.url = url
    link.icon = icon
    link.is_public = True
    link.build()
    return link

def about_link():
    link = AppLink()
    link.name = "关于"
    link.url = xconfig.WebConfig.about_url
    link.icon = "info-circle"
    link.is_public = True
    return link


SYS_TOOLS = [
    user_link("设置",   "/system/settings", "cog"),
    guest_link("登录", "/login", "sign-in"),

    admin_link("系统信息",   "/system/info", "info-circle"),
    admin_link("文件",       "/fs_list", "file-text-o"),
    admin_link("定时任务",   "/system/crontab", "clock-o"),
    admin_link("任务列表", "/admin/jobs"),
    admin_link("事件注册", "/system/event"),
    admin_link("线程管理", "/system/thread_info"),
    admin_link("Menu_User",   "/system/user/list", "users"),
    admin_link("Menu_Log",    "/system/log"),
    admin_link("Menu_Modules",  "/system/modules_info"),
    admin_link("Shell",    "/tools/shell", "terminal"),
    admin_link("集群管理", "/system/sync?p=home", "server"),

    user_link("Menu_Plugin",   "/plugin_category_list?category=index&show_back=true", "cogs"),
    # 关于链接，支持外链
    about_link(),
]

NOTE_TOOLS = [
    user_link("笔记本", "/note/group", "book"),
    user_link("待办",  "/message?tag=task", "calendar-check-o"),
    user_link("随手记",  "/message?tag=log", "pencil"),
    user_link("标签列表", "/note/taglist", "tags"),

    # 笔记
    user_link("最近更新", "/note/recent?orderby=update", "edit"),
    user_link("最近创建", "/note/recent?orderby=create", "plus"),
    user_link("最近查看", "/note/recent?orderby=view", "eye"),
    user_link("常用笔记", "/note/recent?orderby=myhot", "star-o"),
    user_link("时光轴", "/note/timeline?type=all"),
    user_link("词典", "/note/dict", img_src="/static/image/icon_dict.svg"),
    user_link("搜索历史", "/search", "search"),
    user_link("上传管理", "/fs_upload", "upload"),
    user_link("数据统计", "/note/stat", "bar-chart"),
    user_link("月度计划", "/plan/month", "calendar"),
]

DATA_TOOLS = [
    admin_link("数据库", "/system/sqldb_admin?p=sqldb", "database"),
    admin_link("缓存管理", "/system/cache", "database"),
    # admin_link("消息队列", "/system/todo", "database"),
]

# 所有功能配置
xconfig.MENU_LIST = [
    Storage(name="Note", children=NOTE_TOOLS, need_login=True),
    Storage(name="System", children=SYS_TOOLS, need_login=True),
    Storage(name="数据管理", children=DATA_TOOLS, need_login=True),
    # TODO 增加一栏自定义的插件
]

xconfig.NOTE_OPTIONS = [
    link("New_Note", "/note/add"),
    link("Recent Updated", "/note/recent_edit"),
    link("Recent Created", "/note/recent_created"),
    link("Recent View",  "/note/recent_viewed"),
    link("Public",   "/note/public"),
    link("Tag List", "/note/taglist"),
]


class IndexHandler:

    def GET(self):
        arg_show_back = xutils.get_argument_bool("show_back")
        arg_show_menu = xutils.get_argument_bool("show_menu", default_value=True)
        user_name = xauth.current_name()
        menu_list = []

        def filter_link_func(link):
            if link.is_guest:
                return user_name is None
            if link.is_user:
                return user_name != None
            if link.user == "" or link.user == None:
                return True
            return link.user == user_name

        for category in xconfig.MENU_LIST:
            children = category.children
            if len(children) == 0:
                continue
            children = list(filter(filter_link_func, children))
            menu_list.append(Storage(name=category.name, children=children))

        kw = Storage()
        kw.Storage = Storage
        kw.user = xauth.get_current_user()
        kw.menu_list = menu_list
        kw.html_title = "系统"
        kw.show_back = arg_show_back
        kw.show_menu = arg_show_menu

        return xtemplate.render("system/page/system_index.html", **kw)


class AdminHandler:

    @xauth.login_required("admin")
    def GET(self):
        if webutil.is_desktop_client():
            raise web.found("/system/info")
        return xtemplate.render("system/page/system_admin.html")


class ReloadHandler:

    @xauth.login_required("admin")
    def GET(self):
        # autoreload will load new handlers
        import web

        runtime_id = xutils.get_argument_str("runtime_id")
        if runtime_id == xconfig.RUNTIME_ID:
            # autoreload.reload()
            xmanager.restart()
            raise web.seeother("/system/index")
        else:
            return dict(code="success", status="running")

    def POST(self):
        return self.GET()


class UserCssHandler:

    def GET(self):
        web.header("Content-Type", "text/css")
        environ = web.ctx.environ
        path = os.path.join(xconfig.SCRIPTS_DIR, "user.css")
        web.header("Cache-Control", "max-age=3600")

        if not os.path.exists(path):
            return b''

        etag = '"%s"' % os.path.getmtime(path)
        client_etag = environ.get('HTTP_IF_NONE_MATCH')
        web.header("Etag", etag)
        if etag == client_etag:
            web.ctx.status = "304 Not Modified"
            return b''  # 其实webpy已经通过yield空bytes来避免None
        return xutils.readfile(path)
        # return xconfig.get("USER_CSS", "")


class UserJsHandler:

    def GET(self):
        web.header("Content-Type", "application/javascript")
        web.header("Cache-Control", "max-age=3600")
        path = os.path.join(xconfig.SCRIPTS_DIR, "user.js")
        if not os.path.exists(path):
            return ""
        return xutils.readfile(path)


xutils.register_func("url:/system/index", IndexHandler)

xurls = (
    r"/system/sys",   IndexHandler,
    r"/system/index", IndexHandler,
    r"/system/admin", AdminHandler,
    r"/system/system", IndexHandler,
    r"/system/reload", ReloadHandler,
    r"/system/user\.css", UserCssHandler,
    r"/system/user\.js", UserJsHandler,
)
