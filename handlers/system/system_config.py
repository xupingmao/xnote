
from xutils import Storage
from xnote.core import xconfig

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
    admin_link("任务实例", "/admin/jobs"),
    admin_link("事件注册", "/system/event"),
    admin_link("线程管理", "/system/thread_info"),
    admin_link("Menu_User",   "/system/user/list", "users"),
    admin_link("Menu_Log",    "/system/log"),
    admin_link("Menu_Modules",  "/system/modules_info"),
    admin_link("Shell",    "/tools/shell", "terminal"),
    admin_link("集群管理", "/system/sync?p=home", "server"),
    admin_link("开发者", "/plugin_list?category=develop", icon="fa-code"),

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
    user_link("我的动态", "/note/recent?orderby=update", icon="paper-plane"),
    # user_link("最近创建", "/note/recent?orderby=create", "plus"),
    # user_link("最近查看", "/note/recent?orderby=view", "eye"),
    # user_link("常用笔记", "/note/recent?orderby=myhot", "star-o"),
    user_link("时光轴", "/note/timeline?type=all", icon="hourglass-start"),
    # 词典可以用 language 图标
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


def init():
    pass
