# -*- coding: utf-8 -*-
"""系统配置（菜单、链接等），作为 config 包的私有模块"""
from typing import List, Optional

from xutils import Storage
from xnote.core import xconfig


class AppLink:
    name: str
    url: str
    user: str
    is_admin: bool
    is_user: bool
    is_guest: bool
    is_public: bool
    icon: Optional[str]
    img_src: Optional[str]

    def __init__(self) -> None:
        self.name = ""
        self.url = ""
        self.user = ""
        self.is_admin = False
        self.is_user = False
        self.is_guest = False
        self.is_public = False
        self.icon = None
        self.img_src = None

    def build(self) -> None:
        self.url = xconfig.WebConfig.server_home + self.url
        if self.img_src != None:
            self.img_src = xconfig.WebConfig.server_home + self.img_src


def link(name: str, url: str, user: str = "", icon: str = "cube") -> AppLink:
    result = AppLink()
    result.name = name
    result.url = url
    result.user = user
    result.icon = icon
    result.build()
    return result


def admin_link(name: str, url: str, icon: str = "cube", img_src: Optional[str] = None) -> AppLink:
    link = AppLink()
    link.name = name
    link.url = url
    link.icon = icon
    link.is_admin = True
    link.user = "admin"
    link.img_src = img_src
    link.build()
    return link


def user_link(name: str, url: str, icon: str = "cube", img_src: Optional[str] = None) -> AppLink:
    link = AppLink()
    link.name = name
    link.url = url
    link.icon = icon
    link.img_src = img_src
    link.is_user = True
    link.build()
    return link


def guest_link(name: str, url: str, icon: str = "cube") -> AppLink:
    link = AppLink()
    link.name = name
    link.url = url
    link.icon = icon
    link.is_guest = True
    link.build()
    return link


def public_link(name: str, url: str, icon: str = "cube") -> AppLink:
    link = AppLink()
    link.name = name
    link.url = url
    link.icon = icon
    link.is_public = True
    link.build()
    return link


def about_link() -> AppLink:
    link = AppLink()
    link.name = "关于"
    link.url = xconfig.WebConfig.about_url
    link.icon = "info-circle"
    link.is_public = True
    return link


SYS_TOOLS: List[AppLink] = [
    user_link("设置",   "/system/settings", "cog"),
    guest_link("登录", "/login", "sign-in"),

    admin_link("系统信息",   "/system/info", "info-circle"),
    admin_link("Menu_User",   "/system/user/list", "users"),
    admin_link("文件",       "/fs_list", "file-text-o"),
    admin_link("定时任务",   "/system/crontab", "clock-o"),
    admin_link("任务实例", "/admin/jobs"),
    admin_link("事件注册", "/system/event"),
    admin_link("线程管理", "/system/thread_info"),
    admin_link("Menu_Log",    "/system/log/db"),
    admin_link("Shell",    "/tools/shell", img_src="/_static/image/icons/icon_terminal.png"),
    admin_link("集群管理", "/system/sync?p=home", "server"),
    admin_link("开发者", "/plugin_list?category=develop", icon="fa-code"),

    user_link("Menu_Plugin",   "/plugin_category_list?category=index&show_back=true", "cogs"),
    # 关于链接，支持外链
    about_link(),
]

NOTE_TOOLS: List[AppLink] = [
    user_link("笔记本", "/note/group", "book"),
    user_link("待办",  "/message/task", "calendar-check-o"),
    user_link("随手记",  "/message?tag=log", "pencil"),
    user_link("标签列表", "/note/taglist", "tags"),

    # 笔记
    user_link("我的动态", "/note/recent?orderby=update", icon="paper-plane"),
    user_link("时光轴", "/note/timeline?type=all", icon="hourglass-start"),
    # 词典可以用 language 图标
    user_link("词典", "/note/dict", img_src="/_static/image/icon_dict.svg"),
    user_link("搜索历史", "/search", "search"),
    user_link("上传管理", "/fs_upload/manage", "upload"),
    user_link("数据统计", "/note/stat", "bar-chart"),
    user_link("日历", "/note/calendar", "calendar"),
    user_link("聊天助手", "/chatbot", "comments"),
]

DATA_TOOLS: List[AppLink] = [
    admin_link("数据库", "/system/sqldb_admin?p=sqldb", "database"),
    admin_link("缓存管理", "/system/cache", "database"),
    admin_link("数据修复", "/admin/repair", "wrench"),
    # admin_link("消息队列", "/system/todo", "database"),
]


class MenuGroup:
    name: str
    children: List[AppLink]
    need_login: bool

    def __init__(self, name: str = "", children: List[AppLink] = [], need_login: bool = True) -> None:
        self.name = name
        self.children = children
        self.need_login = need_login


# 所有功能配置
MENU_LIST: List[MenuGroup] = [
    MenuGroup(name="Note", children=NOTE_TOOLS),
    MenuGroup(name="System", children=SYS_TOOLS),
    MenuGroup(name="数据管理", children=DATA_TOOLS),
    # TODO 增加一栏自定义的插件
]
