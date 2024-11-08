# encoding=utf-8
# @since 2024/11/02
import xutils
from xnote.core import xconfig
from xnote.plugin import PluginContext
from .models import PluginCategory

def inner_plugin(name, url, category="inner", url_query="", icon= "fa fa-cube"):
    context = PluginContext()
    context.name = name
    context.title = name
    context.url = url
    context.url_query = url_query
    context.editable = False
    context.category = category
    context.permitted_role_list = ["admin", "user"]
    context.require_admin = False
    context.icon = icon
    context.icon_class = icon
    context.build()
    return context


def note_plugin(name, url, icon=None, required_role="user", url_query=""):
    context = PluginContext()
    context.name = name
    context.title = name
    context.url = url
    context.url_query = url_query
    context.icon = icon
    context.icon_class = "fa %s" % icon
    context.editable = False
    context.category = "note"
    context.require_admin = False
    context.required_role = required_role
    context.permitted_role_list = ["admin", "user"]
    context.is_builtin = True
    context.build()
    return context


def index_plugin(name, url, url_query=""):
    return inner_plugin(name, url, "index", url_query=url_query)


def file_plugin(name, url, icon= "fa fa-cube"):
    return inner_plugin(name, url, "dir", icon=icon)


def dev_plugin(name, url):
    return inner_plugin(name, url, "develop")


def system_plugin(name, url):
    return inner_plugin(name, url, "system")


def load_inner_tools():
    pass


INNER_TOOLS = [
    # 工具集/插件集
    # index_plugin("笔记工具", "/plugin_list?category=note", url_query = "&show_back=true"),
    # index_plugin("文件工具", "/plugin_list?category=dir" , url_query = "&show_back=true"),
    # index_plugin("开发工具", "/plugin_list?category=develop", url_query = "&show_back=true"),
    # index_plugin("网络工具", "/plugin_list?category=network", url_query = "&show_back=true"),
    # index_plugin("系统工具", "/plugin_list?category=system" , url_query = "&show_back=true"),

    # 开发工具
    dev_plugin("浏览器信息", "/tools/browser_info"),

    # 文本
    dev_plugin("文本对比", "/tools/text_diff"),
    dev_plugin("文本转换", "/tools/text_convert"),
    dev_plugin("随机字符串", "/tools/random_string"),

    # 图片
    dev_plugin("图片合并", "/tools/img_merge"),
    dev_plugin("图片拆分", "/tools/img_split"),
    dev_plugin("图像灰度化", "/tools/img2gray"),

    # 编解码
    dev_plugin("base64", "/tools/base64"),
    dev_plugin("HEX转换", "/tools/hex"),
    dev_plugin("md5签名", "/tools/md5"),
    dev_plugin("sha1签名", "/tools/sha1"),
    dev_plugin("URL编解码", "/tools/urlcoder"),
    dev_plugin("条形码", "/tools/barcode"),
    dev_plugin("二维码", "/tools/qrcode"),
    dev_plugin("插件目录v2", "/plugin_list_v2"),

    # 其他工具
    inner_plugin("分屏模式", "/tools/multi_win"),
    inner_plugin("RunJS", "/tools/runjs"),
    inner_plugin("摄像头", "/tools/camera"),

    # 笔记工具
    note_plugin("新建笔记", "/note/create", "fa-plus-square"),
    note_plugin("我的置顶", "/note/sticky", "fa-thumb-tack"),
    note_plugin("搜索历史", "/search/history", "fa-search"),
    note_plugin("导入笔记", "/note/html_importer",
                "fa-internet-explorer", required_role="admin"),
    note_plugin("时间视图", "/note/date", "fa-clock-o",
                url_query="?show_back=true"),
    note_plugin("数据统计", "/note/stat", "fa-bar-chart"),
    note_plugin("上传管理", "/fs_upload", "fa-upload"),
    note_plugin("笔记批量管理", "/note/management", "fa-gear"),
    note_plugin("回收站", "/note/removed", "fa-trash"),
    note_plugin("笔记本", "/note/group", "fa-th-large"),
    note_plugin("待办任务", "/message?tag=task", "fa-calendar-check-o"),
    note_plugin("随手记", "/message?tag=log", "fa-file-text-o"),
    note_plugin("我的相册", "/note/gallery", "fa-photo"),
    note_plugin("我的清单", "/note/list", "fa-list"),
    note_plugin("我的日志", "/note/log", "fa-file-text-o"),
    note_plugin("我的评论", "/note/comment/mine", "fa-comments"),
    note_plugin("标签列表", "/note/taglist", "fa-tags"),
    note_plugin("常用笔记", "/note/recent?orderby=hot", "fa-file-text-o"),
    note_plugin("词典", "/note/dict", "icon-dict"),
    note_plugin("时光轴", "/note/timeline", "fa-clock-o"),
    note_plugin("笔记日历", "/note/group?type=year", "fa-file-text-o"),

    # 文件工具
    file_plugin("文件索引", "/fs_index"),
    file_plugin("我的收藏夹", "/fs_bookmark", icon="fa fa-folder"),

    # 系统工具
    system_plugin("系统日志", "/system/log"),
]
