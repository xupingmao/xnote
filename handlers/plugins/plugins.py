# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/09/30 20:53:38
# @modified 2021/01/02 20:23:04
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
import copy
from xtemplate import BasePlugin
from xutils import History
from xutils import cacheutil
from xutils import Storage
from xutils import fsutil
from xutils import textutil, SearchResult, dateutil, dbutil, u


"""xnote插件模块，由于插件的权限较大，开发权限只开放给管理员，普通用户可以使用

插件的模型：插件包含两部分，程序和数据，程序部分存储在插件目录中的文件，数据存储在数据库或者文件中，使用dbutil/fsutil接口操作数据
- 插件名称、描述、文件名、文件路径
- 插件的主类
- 插件的分类
- 插件的访问权限

插件的生命周期
- 插件的注册：debug模式下实时注册，非debug模式：初始化注册+按需注册
- 插件的卸载：退出应用
- 插件的刷新：刷新系统的时候重新加载
- 插件的删除：删除插件文件

插件日志：
- 日志关系：每个用户保留一个插件访问记录，记录最近访问的时间，访问的总次数
- 日志的创建：访问的时候创建
- 日志的更新：访问的时候更新
- 日志的删除：暂无

"""

dbutil.register_table("plugin_visit_log", "插件访问日志")

class PluginContext(Storage):

    def __init__(self):
        self.title         = ""
        self.name          = ""
        self.url           = ""
        self.description   = ""
        self.fname         = ""
        self.fpath         = ""
        self.category      = ""
        self.required_role = ""
        self.atime         = ""
        self.editable      = True
        self.edit_link     = ""
        self.clazz         = None
        self.priority      = 0
        self.icon          = "fa fa-cube"

    # sort方法重写__lt__即可
    def __lt__(self, other):
        return self.title < other.title

    # 兼容Python2
    def __cmp__(self, other):
        return cmp(self.title, other.title)

def is_plugin_file(fpath):
    return os.path.isfile(fpath) and fpath.endswith(".py")

def load_plugin_file(fpath, fname = None):
    if not is_plugin_file(fpath):
        return
    if fname is None:
        fname = os.path.basename(fpath)
    dirname = os.path.dirname(fpath)

    # 相对于插件目录的名称
    plugin_name = fsutil.get_relative_path(fpath, xconfig.PLUGINS_DIR)

    vars = dict()
    vars["script_name"] = plugin_name
    vars["fpath"] = fpath

    try:
        module = xutils.load_script(fname, vars, dirname = dirname)
        main_class = vars.get("Main")
        if main_class != None:
            # 实例化插件
            main_class.fname      = fname
            main_class.fpath      = fpath
            instance              = main_class()
            context               = PluginContext()
            context.fname         = fname
            context.fpath         = fpath
            context.name          = os.path.splitext(fname)[0]
            context.title         = getattr(instance, "title", "")
            context.category      = xutils.attrget(instance, "category")
            context.required_role = xutils.attrget(instance, "required_role")
            context.url           = "/plugins/%s" % plugin_name
            context.clazz         = main_class
            context.edit_link     = "code/edit?path=" + fpath
            context.link          = context.url

            # 初始化插件
            if hasattr(main_class, 'on_init'):
                instance.on_init(context)

            # 注册插件
            xconfig.PLUGINS_DICT[plugin_name] = context
            return context
    except:
        # TODO 增加异常日志
        xutils.print_exc()

def load_inner_plugins():
    for tool in INNER_TOOLS:
        xconfig.PLUGINS_DICT[tool.url] = tool

def load_plugins(dirname = None):
    if dirname is None:
        dirname = xconfig.PLUGINS_DIR

    xconfig.PLUGINS_DICT = {}
    for root, dirs, files in os.walk(dirname):
        for fname in files:
            fpath = os.path.join(root, fname)
            load_plugin_file(fpath)

    load_inner_plugins()

@xutils.timeit(logfile=True, logargs=True, name="FindPlugins")
def find_plugins(category, orderby=None):
    role = xauth.get_current_role()
    user_name = xauth.current_name()
    plugins = []

    if role is None:
        # not logged in
        return plugins

    if category == "None":
        category = None

    for fname in xconfig.PLUGINS_DICT:
        p = xconfig.PLUGINS_DICT.get(fname)
        if p and p.category == category:
            required_role = p.required_role
            if role == "admin" or required_role is None or required_role == role:
                plugins.append(p)
    return sorted_plugins(user_name, plugins, orderby)

def inner_plugin(name, url, category = "inner"):
    context = PluginContext()
    context.name = name
    context.title = name
    context.url   = url
    context.link  = url
    context.editable = False
    context.category = category
    return context

def note_plugin(name, url, icon=None, size = None):
    context = PluginContext()
    context.name = name
    context.title = name
    context.url   = url
    context.link  = url
    context.icon  = icon
    context.size  = size
    context.editable = False
    context.category = "note"
    return context


INNER_TOOLS = [
    # 工具集/插件集
    inner_plugin("笔记工具集合", "/note/tools"),
    inner_plugin("文件工具集合", "/fs_tools"),

    inner_plugin("浏览器信息", "/tools/browser_info"),
    # 文本
    inner_plugin("文本对比", "/tools/text_diff"),
    inner_plugin("文本转换", "/tools/text_convert"),
    inner_plugin("随机字符串", "/tools/random_string"),
    # 图片
    inner_plugin("图片合并", "/tools/img_merge"),
    inner_plugin("图片拆分", "/tools/img_split"),
    inner_plugin("图像灰度化", "/tools/img2gray"),
    # 编解码
    inner_plugin("base64", "/tools/base64"),
    inner_plugin("HEX转换", "/tools/hex"),
    inner_plugin("md5签名", "/tools/md5"),
    inner_plugin("sha1签名", "/tools/sha1"),
    inner_plugin("URL编解码", "/tools/urlcoder"),
    inner_plugin("条形码", "/tools/barcode"),
    inner_plugin("二维码", "/tools/qrcode"),
    # 其他工具
    inner_plugin("分屏模式", "/tools/multi_win"),
    inner_plugin("RunJS", "/tools/runjs"),
    inner_plugin("摄像头", "/tools/camera"),

    # 笔记工具
    note_plugin("置顶笔记", "/note/sticky", "fa-thumb-tack"),
    note_plugin("搜索历史", "/search/history", "fa-search"),
    note_plugin("导入笔记", "/note/html_importer", "fa-internet-explorer"),
    note_plugin("日历视图", "/note/calendar", "fa-calendar"),
    note_plugin("时间视图", "/note/date", "fa-clock-o"),
    note_plugin("数据统计", "/note/stat", "fa-bar-chart"),
    note_plugin("上传管理", "/fs_upload", "fa-upload"),
    note_plugin("回收站", "/note/removed", "fa-trash"),
    note_plugin("笔记本", "/note/group", "fa-th-large"),
    note_plugin("任务列表", "/message?tag=task", "fa-calendar-check-o"),
    note_plugin("备忘记事", "/message?tag=log", "fa-sticky-note"),
    note_plugin("相册", "/note/gallery", "fa-photo"),
    note_plugin("清单", "/note/list", "fa-list"),
    note_plugin("词典", "/note/dict", "icon-dict"),
]

def get_inner_tool_name(url):
    for tool in INNER_TOOLS:
        if tool.url == url:
            return tool.name
    return url

def build_inner_tools():
    return copy.copy(INNER_TOOLS)

def build_plugin_links(plugins):
    return plugins

def sorted_plugins(user_name, plugins, orderby=None):
    # 把最近访问的放在前面
    logs = list_visit_logs(user_name)
    
    # 构造url到插件的映射
    url_dict = dict()
    for p in plugins:
        url_dict[p.url] = p

    recent_plugins = []
    recent_urls    = []

    # 通过日志里的url找插件
    for log in logs:
        if log.url in url_dict:
            recent_plugins.append(url_dict[log.url])
            recent_urls.append(log.url)
            del url_dict[log.url]

    rest_plugins = list(filter(lambda x:x.url not in recent_urls, plugins))
    return recent_plugins + rest_plugins

def list_plugins(category, sort = True):
    if category == "other":
        plugins = find_plugins(None)
        links   = build_plugin_links(plugins)
    elif category and category != "all":
        # 某个分类的插件
        plugins = find_plugins(category)
        links   = build_plugin_links(plugins)
    else:
        # 所有插件
        links = build_inner_tools()
        links += build_plugin_links(xconfig.PLUGINS_DICT.values())

    user_name = xauth.current_name()
    if sort:
        return sorted_plugins(user_name, links)
    return links

def find_plugin_by_url(url):
    plugins = list_plugins("all", sort = False)
    for p in plugins:
        if u(p.url) == u(url):
            return p
    return None

def list_recent_plugins():
    user_name = xauth.current_name()
    items = list_visit_logs(user_name)
    links = [find_plugin_by_url(log.url) for log in items]

    return list(filter(None, links))

def list_visit_logs(user_name, offset = 0, limit = -1):
    logs = dbutil.prefix_list("plugin_visit_log:%s" % user_name, 
        offset = offset, limit = limit, reverse = True)
    logs.sort(key = lambda x: x.time, reverse = True)
    return logs

def find_visit_log(user_name, url):
    for key, log in dbutil.prefix_iter("plugin_visit_log:%s" % user_name, include_key = True):
        if log.url == url:
            log.key = key
            return log
    return None

def update_visit_log(log, name):
    log.name = name
    log.time = dateutil.format_datetime()
    if log.visit_cnt is None:
        log.visit_cnt = 1
    log.visit_cnt += 1
    dbutil.put(log.key, log)

def add_visit_log(user_name, url, name = None):
    exist_log = find_visit_log(user_name, url)
    if exist_log != None:
        update_visit_log(exist_log, name)
        return

    log = Storage()
    log.name = name
    log.url  = url
    log.time = dateutil.format_datetime()

    dbutil.insert("plugin_visit_log:%s" % user_name, log)

def delete_visit_log(user_name, name, url):
    exist_log = find_visit_log(user_name, url)
    if exist_log != None:
        dbutil.delete(exist_log.key)

def load_plugin(name):
    user_name = xauth.current_name()
    context   = xconfig.PLUGINS_DICT.get(name)

    # DEBUG模式下始终重新加载插件
    if xconfig.DEBUG or context is None:
        fpath = os.path.join(xconfig.PLUGINS_DIR, name)
        fpath = xutils.get_real_path(fpath)
        if not os.path.exists(fpath):
            return None
        # 发现了新的插件，重新加载一下
        plugin = load_plugin_file(fpath)
        if plugin:
            return plugin
        else:
            return None
    else:
        return context

@xmanager.searchable()
def on_search_plugins(ctx):
    if not xauth.is_admin():
        return
    if not ctx.search_tool:
        return
    if ctx.search_dict:
        return

    results = []

    for plugin in search_plugins(ctx.key):
        result           = SearchResult()
        result.category  = "plugin"
        result.icon      = "fa-cube"
        result.name      = u(plugin.name)
        result.name      = u(plugin.title + "(" + plugin.name + ")")
        result.url       = u(plugin.url)
        result.edit_link = plugin.edit_link
        results.append(result)

    result_count = len(results)
    if ctx.category != "plugin" and len(results) > 3:
        results = results[:3]
        more = SearchResult()
        more.name = u("查看更多插件(%s)") % result_count
        more.icon = "fa-cube"
        more.url  = "/plugins_list?category=plugin&key=" + ctx.key
        results.append(more)
    ctx.tools += results

def is_plugin_matched(p, words):
    return textutil.contains_all(p.title, words) \
        or textutil.contains_all(p.url, words) \
        or textutil.contains_all(p.fname, words)


def search_plugins(key):
    from xutils.functions import dictvalues
    words   = textutil.split_words(key)
    plugins = list_plugins("all")
    result  = dict()
    for p in plugins:
        if is_plugin_matched(p, words):
            result[p.url] = p
    return dictvalues(result)


class PluginsListHandler:

    @xauth.login_required()
    def GET(self):
        category = xutils.get_argument("category", "")
        key      = xutils.get_argument("key", "")
        header   = xutils.get_argument("header", "")

        if xauth.is_admin():
            if key != "" and key != None:
                recent  = []
                plugins = search_plugins(key)
            else:
                recent   = list_recent_plugins()
                plugins  = list_plugins(category)
        else:
            recent = []
            if category == "" or category == "all":
                plugins = build_inner_tools()
            else:
                plugins = []

        return xtemplate.render("plugins/page/plugins_v3.html", 
            category = category,
            html_title = "插件",
            header     = header,
            show_aside = xconfig.OPTION_STYLE == "aside",
            search_type = "plugin",
            recent     = recent,
            plugins    = plugins)

def get_plugin_category(category):
    plugin_categories = []

    recent   = list_recent_plugins()
    plugins  = list_plugins(category)
    note_plugins = list_plugins("note")
    dev_plugins  = list_plugins("develop")
    sys_plugins  = list_plugins("system")
    dir_plugins  = list_plugins("dir")
    net_plugins  = list_plugins("network")
    other_plugins = list(filter(lambda x: x.category not in ("inner", "note", "develop", "system", "dir", "network"), plugins))

    plugin_categories.append(["最近", recent])
    plugin_categories.append(["默认工具", build_inner_tools()])
    plugin_categories.append(["笔记", note_plugins])
    plugin_categories.append(["开发工具", dev_plugins])
    plugin_categories.append(["系统", sys_plugins])
    plugin_categories.append(["文件", dir_plugins])
    plugin_categories.append(["网络", net_plugins])
    plugin_categories.append(["其他", other_plugins])
    return plugin_categories

class PluginsGridHandler:

    @xauth.login_required()
    def GET(self):
        category = xutils.get_argument("category", "")
        key      = xutils.get_argument("key", "")
        plugin_categories = []

        if xauth.is_admin():
            if key != None and key != "":
                plugin_categories.append(["搜索", search_plugins(key)])
            else:
                plugin_categories = get_plugin_category(category)
        else:
            plugins = build_inner_tools()
            plugin_categories.append(["默认工具", plugins])

        return xtemplate.render("plugins/page/plugins_v2.html", 
            category = category,
            html_title = "插件",
            plugin_categories = plugin_categories)

class LoadPluginHandler:

    def GET(self, name = ""):
        user_name = xauth.current_name()
        name      = xutils.unquote(name)

        if not name.endswith(".py"):
            name += ".py"
        try:
            url = "/plugins/" + name
            plugin = load_plugin(name)
            if plugin != None:
                # 访问日志
                add_visit_log(user_name, url)
                plugin.atime = dateutil.format_datetime()
                # 渲染页面
                return plugin.clazz().render()
            else:
                # 删除日志
                delete_visit_log(user_name, name, url)
                return xtemplate.render("error.html", 
                    error = "plugin `%s` not found!" % name)
        except:
            error = xutils.print_exc()
            return xtemplate.render("error.html", error=error)

    def POST(self, name = ""):
        return self.GET(name)

class LoadInnerToolHandler:
    
    def GET(self, name):
        user_name = xauth.current_name()
        url  = "/tools/" + name
        fname = xutils.unquote(name)
        if not name.endswith(".html"):
            fname += ".html"
        # Chrome下面 tools/timeline不能正常渲染
        web.header("Content-Type", "text/html")
        fpath = os.path.join(xconfig.HANDLERS_DIR, "tools", fname)
        if os.path.exists(fpath):
            if user_name != None:
                tool_name = get_inner_tool_name(url)
                add_visit_log(user_name, url)
            return xtemplate.render("tools/" + fname, show_aside = False)
        else:
            raise web.notfound()

    def POST(self, name):
        return self.GET(name)

class PluginLogHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        logs = list_visit_logs(user_name)
        return logs

@xmanager.listen("sys.reload")
def reload_plugins(ctx):
    load_plugins()

xutils.register_func("plugin.find_plugins", find_plugins)
xutils.register_func("plugin.add_visit_log", add_visit_log)

xurls = (
    r"/plugins_list_new", PluginsGridHandler,
    r"/plugins_list", PluginsListHandler,
    r"/plugins_log", PluginLogHandler,
    r"/plugins/(.+)", LoadPluginHandler,
    r"/tools/(.+)", LoadInnerToolHandler,
)
