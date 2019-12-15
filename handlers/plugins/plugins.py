# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/09/30 20:53:38
# @modified 2019/12/15 17:56:55
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
from xutils import textutil, SearchResult, u

MAX_HISTORY = 200

def link(name, url, title = ""):
    if title == "":
        title = name
    return Storage(name = name, 
        url = url, 
        link = url, 
        title = title, 
        fname = name,
        editable = False, 
        atime = "")

def inner_link(name, url):
    return Storage(name = name, 
        url = url, 
        link = url, 
        fname = name,
        title = name, 
        editable = False, 
        category = "inner", 
        atime="")

INNER_TOOLS = [
    inner_link("浏览器信息", "/tools/browser_info"),
    # 文本
    inner_link("代码模板", "/tools/code_template"),
    inner_link("文本对比", "/tools/js_diff"),
    inner_link("文本转换", "/tools/text_processor"),
    inner_link("随机字符串", "/tools/random_string"),
    # 图片
    inner_link("图片合并", "/tools/img_merge"),
    inner_link("图片拆分", "/tools/img_split"),
    inner_link("图像灰度化", "/tools/img2gray"),
    # 编解码
    inner_link("base64", "/tools/base64"),
    inner_link("HEX转换", "/tools/hex"),
    inner_link("md5签名", "/tools/md5"),
    inner_link("sha1签名", "/tools/sha1"),
    inner_link("URL编解码", "/tools/urlcoder"),
    inner_link("条形码", "/tools/barcode"),
    inner_link("二维码", "/tools/qrcode"),
    # 其他工具
    inner_link("分屏模式", "/tools/multi_win"),
    inner_link("RunJS", "/tools/runjs"),
]

def build_inner_tools():
    return copy.copy(INNER_TOOLS)

def build_plugin_links(plugins):
    links = []
    for plugin in plugins:
        fname = plugin.fname
        fpath = plugin.fpath

        item = link(plugin.title, plugin.url)
        item.editable = True
        atime = cacheutil.zscore("plugins.history", plugin.name)
        if atime:
            item.atime = xutils.format_date(atime)
        else:
            item.atime = ""

        item.edit_link = "/code/edit?path=" + fpath
        item.title = plugin.title
        item.fname = plugin.fname

        links.append(item)

    return links

def list_plugins(category):
    if category == "other":
        plugins = xmanager.find_plugins(None)
        links = build_plugin_links(plugins)
    elif category and category != "all":
        # 某个分类的插件
        plugins = xmanager.find_plugins(category)
        links = build_plugin_links(plugins)
    else:
        # 所有插件
        links = build_inner_tools()
        links += build_plugin_links(xconfig.PLUGINS_DICT.values())    
    return links

def find_plugin_by_name(name):
    plugins = list_plugins("all")
    name, ext = os.path.splitext(name)
    for p in plugins:
        if u(p.name) == u(name):
            return p
    return None

def list_recent_plugins():
    items = cacheutil.zrange("plugins.history", -6, -1)
    print(items)
    links = [find_plugin_by_name(name) for name in items]
    links.reverse()
    return list(filter(None, links))

def log_plugin_visit(name):
    try:
        fname = xutils.unquote(name)
        cacheutil.zadd("plugins.history", time.time(), fname)
    except TypeError:
        cacheutil.delete("plugins.history")
        cacheutil.zadd("plugins.history", time.time(), fname)

def load_plugin(name):
    log_plugin_visit(name)
    context = xconfig.PLUGINS_DICT.get(name)
    if xconfig.DEBUG or context is None:
        script_name = "plugins/" + name
        fpath = os.path.join(xconfig.PLUGINS_DIR, name)
        if not os.path.exists(fpath):
            return None
        vars = dict()
        vars["script_name"] = script_name
        vars["fpath"] = fpath
        xutils.load_script(script_name, vars)
        main_class = vars.get("Main")
        main_class.fpath = fpath
        return main_class
    else:
        return context.clazz

@xmanager.searchable()
def on_search_plugins(ctx):
    if not xauth.is_admin():
        return
    if not ctx.search_tool:
        return
    if ctx.search_dict:
        return
    name    = ctx.key
    results = []
    words   = textutil.split_words(name)
    for name in xconfig.PLUGINS_DICT:
        plugin = xconfig.PLUGINS_DICT[name]
        unquote_name = xutils.unquote(plugin.fname)
        unquote_name, ext = os.path.splitext(unquote_name)
        plugin_context = plugin
        if textutil.contains_all(unquote_name, words) \
                or (textutil.contains_all(plugin_context.title, words)):
            result           = SearchResult()
            result.category  = "plugin"
            result.icon      = "fa-cube"
            result.name      = u(unquote_name)
            if plugin_context != None:
                # result.raw = u(plugin_context.title)
                # result.name = u("插件 %s (%s)") % (u(plugin_context.title), unquote_name)
                if plugin_context.title != None:
                    result.name = u(plugin_context.title + "(" + unquote_name + ")")
            result.url       = u(plugin.url)
            result.edit_link = u("/code/edit?path=" + plugin.fpath)
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

def search_plugins(key):
    words   = textutil.split_words(key)
    plugins = list_plugins("all")
    result  = []
    for p in plugins:
        if textutil.contains_all(p.title, words) or textutil.contains_all(p.url, words) or textutil.contains_all(p.fname, words):
            result.append(p)
    return result


class PluginsListOldHandler:

    @xauth.login_required()
    def GET(self):
        category = xutils.get_argument("category", "")
        key      = xutils.get_argument("key", "")

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

        return xtemplate.render("plugins/plugins_old.html", 
            category = category,
            html_title = "插件",
            show_aside = xconfig.OPTION_STYLE == "aside",
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

class PluginsListHandler:

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

        return xtemplate.render("plugins/plugins.html", 
            category = category,
            html_title = "插件",
            plugin_categories = plugin_categories)

DEFAULT_PLUGIN_TEMPLATE = '''# -*- coding:utf-8 -*-
# @since $since
# @author $author
import os
import re
import math
import time
import web
import xconfig
import xutils
import xauth
import xmanager
import xtables
import xtemplate
from xtemplate import BasePlugin

HTML = """
<!-- Html -->
"""

class Main(BasePlugin):

    title = "PluginName"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network, develop}
    category = None
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 5
        self.writehtml(HTML)

    def on_init(self, context=None):
        # 插件初始化操作
        pass
'''

class NewPluginHandler(BasePlugin):
    """默认的插件声明入口，定义一个叫做Main的类"""

    def handle(self, input):
        self.description = '''请输入插件名称'''
        self.title = '通过模板创建插件'
        self.btn_text = '创建'
        self.rows = 1
        self.editable = False
        if input != '':
            name = os.path.join(xconfig.PLUGINS_DIR, input)
            if not name.endswith(".py"):
                name += ".py"
            if os.path.exists(name):
                return u("文件[%s]已经存在!") % u(name)
            user_name = xauth.current_name()
            code = xconfig.get("NEW_PLUGIN_TEMPLATE", DEFAULT_PLUGIN_TEMPLATE)
            code = code.replace("$since", xutils.format_datetime())
            code = code.replace("$author", user_name)
            xutils.writefile(name, code)
            log_plugin_visit(os.path.basename(name))
            raise web.seeother('/code/edit?path=%s' % name)

DEFAULT_COMMAND_TEMPLATE = '''# -*- coding:utf-8 -*-
# @since $since
# @author $author
import os
import xutils

def main(path = "", confirmed = False, **kw):
    # your code here
    pass
'''

class NewCommandPlugin(BasePlugin):
    """默认的插件声明入口，定义一个叫做Main的类"""

    def handle(self, input):
        self.title = '通过模板创建命令扩展'
        self.description = '''请输入命令扩展名称'''
        self.btn_text = '创建'
        self.rows = 1
        self.editable = False
        if input != '':
            name = os.path.join(xconfig.COMMANDS_DIR, input)
            if not name.endswith(".py"):
                name += ".py"
            if os.path.exists(name):
                return u("文件[%s]已经存在!") % u(name)
            user_name = xauth.get_current_name()
            code = xconfig.get("NEW_COMMAND_TEMPLATE", DEFAULT_COMMAND_TEMPLATE)
            code = code.replace("$since", xutils.format_datetime())
            code = code.replace("$author", user_name)
            xutils.writefile(name, code)
            raise web.seeother('/code/edit?path=%s' % name)


class PluginsHandler:

    def GET(self, name = ""):
        display_name = xutils.unquote(name)
        name = xutils.get_real_path(display_name)
        if not name.endswith(".py"):
            name += ".py"
        try:
            main_class = load_plugin(name)
            if main_class != None:
                return main_class().render()
            else:
                return xtemplate.render("error.html", 
                    error = "plugin `%s` not found!" % name)
        except:
            error = xutils.print_exc()
            return xtemplate.render("error.html", error=error)

    def POST(self, name = ""):
        return self.GET(name)


xurls = (
    r"/plugins_list_new", PluginsListHandler,
    r"/plugins_list", PluginsListOldHandler,
    r"/plugins_new", NewPluginHandler,
    r"/plugins_new/command", NewCommandPlugin,
    r"/plugins/(.+)", PluginsHandler
)
