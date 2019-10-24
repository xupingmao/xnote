# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/09/30 20:53:38
# @modified 2019/10/23 00:20:07
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
    return Storage(name = name, url = url, link = url, title = title, editable = False, atime="")

def inner_link(name, url):
    return Storage(name = name, url = url, link = url, title = name, editable = False, category = "inner", atime="")

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

def build_plugin_links(dirname, fnames):
    links = []
    for fname in fnames:
        fpath = os.path.join(dirname, fname)
        if not os.path.exists(fpath):
            continue
        name, ext = os.path.splitext(fname)
        name = xutils.unquote(name)
        item = link(name, "/plugins/" + name)
        item.editable = True
        # st = os.stat(fpath)
        # item.atime = xutils.format_date(st.st_atime)
        atime = cacheutil.zscore("plugins.history", fname)
        if atime:
            item.atime = xutils.format_date(atime)
        else:
            item.atime = ""

        item.edit_link = "/code/edit?path=" + fpath
        plugin_context = xconfig.PLUGINS.get(fname)
        item.title = ''
        if plugin_context is not None:
            item.title = plugin_context.title
            item.category = plugin_context.category
        else:
            item.title = name
        links.append(item)
    return links

def list_plugins(category):
    dirname = xconfig.PLUGINS_DIR
    if not os.path.isdir(dirname):
        return []

    if category == "other":
        plugins = xmanager.find_plugins(None)
        links = build_plugin_links(dirname, [p.fname for p in plugins])
    elif category and category != "all":
        # 某个分类的插件
        plugins = xmanager.find_plugins(category)
        links = build_plugin_links(dirname, [p.fname for p in plugins])
    else:
        # 所有插件
        recent_names = cacheutil.zrange("plugins.history", -MAX_HISTORY, -1)
        recent_names.reverse()
        plugins_list = os.listdir(dirname)
        plugins_list = set(plugins_list) - set(recent_names)
        links = build_inner_tools()
        links += build_plugin_links(dirname, recent_names + sorted(plugins_list))    
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
    context = xconfig.PLUGINS.get(name)
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
    dirname = xconfig.PLUGINS_DIR
    words   = textutil.split_words(name)
    for fname in xutils.listdir(dirname):
        unquote_name = xutils.unquote(fname)
        unquote_name, ext = os.path.splitext(unquote_name)
        plugin_context = xconfig.PLUGINS.get(fname)
        if textutil.contains_all(unquote_name, words) \
                or (plugin_context != None and textutil.contains_all(plugin_context.title, words)):
            result           = SearchResult()
            result.category  = "plugin"
            result.name      = u("[插件] " + unquote_name)
            if plugin_context != None:
                # result.raw = u(plugin_context.title)
                # result.name = u("插件 %s (%s)") % (u(plugin_context.title), unquote_name)
                if plugin_context.title != None:
                    result.name = u("[插件] " + plugin_context.title + "(" + unquote_name + ")")
            result.url       = u("/plugins/" + unquote_name)
            result.edit_link = u("/code/edit?path=" + os.path.join(dirname, fname))
            results.append(result)
    ctx.tools += results

class PluginsListOldHandler:

    @xauth.login_required()
    def GET(self):
        category = xutils.get_argument("category", "")

        if xauth.is_admin():
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

class PluginsListHandler:

    @xauth.login_required()
    def GET(self):
        category = xutils.get_argument("category", "")
        plugin_categories = []

        if xauth.is_admin():
            recent   = list_recent_plugins()
            plugins  = list_plugins(category)

            # note_plugins = list(filter(lambda x: x.category == "note", plugins))
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
    r"/plugins_list", PluginsListHandler,
    r"/plugins_list_old", PluginsListOldHandler,
    r"/plugins_new", NewPluginHandler,
    r"/plugins_new/command", NewCommandPlugin,
    r"/plugins/(.+)", PluginsHandler
)
