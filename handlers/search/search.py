# encoding=utf-8
# @author xupingmao
# @since 2017/02/19
# @modified 2020/01/28 15:12:11

import re
import os
import sys
import copy
import json
import base64 
import time
import math
import six
import web
import xutils
import xconfig
import xauth
import xmanager
import xtemplate
import xtables
from xutils import textutil, u, cacheutil
from xutils import Queue, History, Storage

NOTE_DAO = xutils.DAO("note")
MSG_DAO  = xutils.DAO("message")

config = xconfig
_RULES = []

class BaseRule:

    def __init__(self, pattern, func, scope="home"):
        self.pattern = pattern
        self.func    = func
        self.scope   = scope

def add_rule(pattern, func_str):
    global _RULES
    try:
        mod, func_name = func_str.rsplit('.', 1)
        # mod = __import__(mod, None, None, [''])
        mod = six._import_module("handlers.search." + mod)
        func = getattr(mod, func_name)
        func.modfunc = func_str
        rule = BaseRule(r"^%s\Z" % u(pattern), func)
        _RULES.append(rule)
    except Exception as e:
        xutils.print_exc()

class SearchContext:

    def __init__(self):
        # 输入的文本
        self.key              = ''
        self.input_text       = ''
        # 正则匹配的分组
        self.groups           = []
        self.user_name        = ''
        self.search_message   = False
        self.search_note      = True
        self.search_note_content = False
        self.search_dict      = False
        self.search_tool      = True
        # 是否继续执行，用于最后兜底的搜索，一般是性能消耗比较大的
        self.stop             = False
        
        # 处理的结果集
        self.commands = []
        self.dicts    = []
        self.tools    = []
        self.notes    = []
        self.messages = []
        self.files    = []

    def join_as_files(self):
        return self.commands + self.dicts + self.tools + self.messages + self.notes + self.files

def fill_note_info(files):
    for file in files:
        if file.category == "note":
            parent = xutils.call("note.get_by_id", file.parent_id)
            if parent is not None:
                file.parent_name = parent.name

def log_search_history(user, key, category = "default", cost_time = 0):
    NOTE_DAO.add_search_history(user, key, category, cost_time)

@xutils.timeit(name = "Search.ListRecent", logargs = True, logfile = True)
def list_search_history(user_name, limit = -1):
    raw_history_list = NOTE_DAO.list_search_history(user_name)
    history_list = []

    for item in raw_history_list:
        if item.key is None:
            continue
        if item.key not in history_list:
            history_list.append(item.key)
    return history_list

def build_search_context(user_name, category, key):
    words                   = textutil.split_words(key)
    ctx                     = SearchContext()
    ctx.key                 = key
    ctx.input_text          = key
    ctx.words               = words
    ctx.category            = category
    ctx.search_message      = (category == "message")
    ctx.search_note_content = (category == "content")
    ctx.search_dict         = (category == "dict")
    ctx.user_name           = user_name

    if ctx.search_message:
        ctx.search_note = False
        ctx.search_note_content = False
        ctx.search_tool = False
    if ctx.search_dict:
        ctx.search_note = False
        ctx.search_tool = False
    if ctx.search_note_content:
        ctx.search_tool = False
    if ctx.category == "book":
        ctx.search_note = False
        ctx.search_tool = False

    return ctx

def apply_search_rules(ctx, key):
    files = []
    for rule in _RULES:
        pattern = rule.pattern
        func = rule.func
        # re.match内部已经实现了缓存
        m = re.match(pattern, key)
        if m:
            try:
                start_time0 = time.time()
                results     = func(ctx, *m.groups())
                cost_time0  = time.time() - start_time0
                xutils.trace("SearchHandler", func.modfunc, int(cost_time0*1000))
                if results is not None:
                    files += results
            except Exception as e:
                xutils.print_exc()
    return files

class handler:

    def do_search(self, page_ctx, key, offset, limit):
        category   = xutils.get_argument("category", "")
        words      = textutil.split_words(key)
        user_name  = xauth.get_current_name()
        start_time = time.time()
        ctx        = build_search_context(user_name, category, key)
        
        # 阻断性的搜索，比如特定语法的
        xmanager.fire("search.before", ctx)
        if ctx.stop:
            return ctx.join_as_files()

        # 普通的搜索行为
        xmanager.fire("search", ctx)

        ctx.files = apply_search_rules(ctx, key)

        cost_time = int((time.time() - start_time) * 1000)
        
        log_search_history(user_name, key, category, cost_time)

        if ctx.stop:
            return ctx.join_as_files()

        # 慢搜索,如果时间过长,这个服务会被降级
        xmanager.fire("search.slow", ctx)
        xmanager.fire("search.after", ctx)

        page_ctx.tools = []

        return ctx.join_as_files()

    def GET(self, path_key = None):
        """search files by name and content"""
        load_rules()
        key       = xutils.get_argument("key", "")
        title     = xutils.get_argument("title", "")
        category  = xutils.get_argument("category", "default")
        page      = xutils.get_argument("page", 1, type = int)
        user_name = xauth.get_current_name()
        page_url  =  "/search/search?key=%s&category=%s&page="\
            % (key, category)
        pagesize = xconfig.SEARCH_PAGE_SIZE
        offset   = (page-1) * pagesize
        limit    = pagesize

        if path_key:
            key = xutils.unquote(path_key)

        if key == "" or key == None:
            return xtemplate.render("search/search_result.html", 
                show_aside = False,
                recent = list_search_history(user_name),
                html_title = "Search",
                category = category, 
                tools    = [],
                files    = [], 
                count    = 0)
        key   = key.strip()
        ctx   = Storage()
        files = self.do_search(ctx, key, offset, pagesize)
        count = len(files)
        files = files[offset:offset+limit]
        fill_note_info(files)
        return xtemplate.render("search/search_result.html", 
            show_aside = False,
            key = key,
            html_title = "Search",
            category = category,
            files    = files, 
            title    = title,
            page_max = int(math.ceil(count/pagesize)),
            page_url = page_url,
            **ctx)

rules_loaded = False
def load_rules():
    global rules_loaded
    if rules_loaded:
        return
    add_rule(r"([^ ]*)",                "api.search")
    add_rule(r"静音(.*)",               "mute.search")
    add_rule(r"mute(.*)",               "mute.search")
    add_rule(r"取消静音",               "mute.cancel")
    add_rule(r"(.*)", "note.search")
    rules_loaded = True

class RulesHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        rules = list_search_rules(user_name)
        return xtemplate.render("search/search_rules.html", rules = rules, show_search = False)

def list_search_rules(user_name):
    list, count = MSG_DAO.list_by_tag(user_name, 'key', 0, 1000)

    for item in list:
        item.url = "/note/timeline?type=search&key=" + xutils.encode_uri_component(item.content)
    return list

xutils.register_func("search.list_rules", list_search_rules)
xutils.register_func("search.list_recent", list_search_history)

xurls = (
    r"/search/search", handler, 
    r"/search", handler,
    r"/search/rules", RulesHandler,
    r"/s/(.+)", handler
)

