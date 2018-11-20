# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/09/30 20:53:38
# @modified 2018/11/20 23:06:14
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
from xutils import textutil, SearchResult, u

def link(name, url):
    return Storage(name = name, url = url, link = url)

def list_plugins():
    dirname = xconfig.PLUGINS_DIR
    if not os.path.isdir(dirname):
        return []
    links = []
    recent_names = cacheutil.zrange("plugins.history", -50, -1)
    recent_names.reverse()
    recent_names = [x + ".py" for x in recent_names]
    plugins_list = os.listdir(dirname)
    plugins_list = set(plugins_list) - set(recent_names)

    for fname in recent_names + sorted(plugins_list):
        fpath = os.path.join(dirname, fname)
        if not os.path.exists(fpath):
            continue
        name, ext = os.path.splitext(fname)
        name = xutils.unquote(name)
        item = link(name, "/plugins/" + name)
        # st = os.stat(fpath)
        # item.atime = xutils.format_date(st.st_atime)
        atime = cacheutil.zscore("plugins.history", name)
        if atime:
            item.atime = xutils.format_date(atime)
        else:
            item.atime = ""

        item.edit_link = "/code/edit?path=" + fpath
        plugin_context = xconfig.PLUGINS.get(fname)
        item.title = ''
        if plugin_context is not None:
            item.title = plugin_context.title
        links.append(item)
    return links

def list_recent_plugins():
    items = cacheutil.zrange("plugins.history", -6, -1)
    links = [dict(name=name, link="/plugins/" + name) for name in items]
    links.reverse()
    return links;

def log_plugin_visit(name):
    try:
        display_name = xutils.unquote(name)
        base_name = os.path.splitext(display_name)[0]
        cacheutil.zadd("plugins.history", time.time(), base_name)
    except TypeError:
        cacheutil.delete("plugins.history")
        cacheutil.zadd("plugins.history", time.time(), base_name)

def load_plugin(name):
    log_plugin_visit(name)
    context = xconfig.PLUGINS.get(name)
    if xconfig.DEBUG or context is None:
        script_name = "plugins/" + name
        if not os.path.exists(os.path.join(xconfig.PLUGINS_DIR, name)):
            return None
        vars = dict()
        vars["script_name"] = script_name
        xutils.load_script(script_name, vars)
        main_class = vars.get("Main")
        return main_class
    else:
        return context.clazz

@xmanager.listen("search")
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
            result.name      = u("插件 - " + unquote_name)
            if plugin_context != None:
                result.raw = u(plugin_context.title)
            result.url       = u("/plugins/" + fname)
            result.edit_link = u("/code/edit?path=" + os.path.join(dirname, fname))
            results.append(result)
    ctx.tools += results

class PluginsListHandler:

    @xauth.login_required("admin")
    def GET(self):
        return xtemplate.render("plugins/plugins.html", 
            html_title = "插件",
            show_aside = xconfig.OPTION_STYLE == "aside",
            recent     = list_recent_plugins(),
            plugins    = list_plugins())

TEMPLATE = '''# -*- coding:utf-8 -*-
# @since $since
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
from xutils import cacheutil
from xtemplate import BasePlugin

class Main(BasePlugin):

    title = "PluginName"
    description = """提示内容"""
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 20

    def on_init(self, context=None):
        # 插件初始化操作
        pass
    
    def command(self):
        pass
'''

class NewPluginHandler(BasePlugin):
    """默认的插件声明入口，定义一个叫做Main的类"""

    def handle(self, input):
        self.description = '''请输入插件名称'''
        self.title = '通过模板创建插件'
        self.btn_text = '创建'
        self.rows = 1
        if input != '':
            name = os.path.join(xconfig.PLUGINS_DIR, input)
            if not name.endswith(".py"):
                name += ".py"
            if os.path.exists(name):
                return "文件[%s]已经存在!" % name
            code = xconfig.get("NEW_PLUGIN_TEMPLATE", TEMPLATE)
            code = code.replace("$since", xutils.format_datetime())
            xutils.savetofile(name, code)
            log_plugin_visit(os.path.basename(name))
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
    r"/plugins_new", NewPluginHandler,
    r"/plugins/(.+)", PluginsHandler
)
