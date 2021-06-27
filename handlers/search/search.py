# encoding=utf-8
# @author xupingmao
# @since 2017/02/19
# @modified 2021/06/27 16:38:02

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
from xutils import textutil, u
from xutils import Queue, Storage
from xutils import dateutil
from xtemplate import T

NOTE_DAO = xutils.DAO("note")
MSG_DAO  = xutils.DAO("message")
DICT_DAO = xutils.DAO("dict")

config = xconfig
_RULES = []

SEARCH_TYPE_DICT = dict()


def register_search_handler(search_type, placeholder = None, action = None, tag = None):
    global SEARCH_TYPE_DICT
    SEARCH_TYPE_DICT[search_type] = Storage(
        placeholder = placeholder,
        action = action,
        tag = tag
    )

def get_search_handler(search_type):
    handler = SEARCH_TYPE_DICT.get(search_type)
    if handler != None:
        return handler

    return SEARCH_TYPE_DICT.get("default")



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
            parent = NOTE_DAO.get_by_id(file.parent_id)
            if parent is not None:
                file.parent_name = parent.name
            file.show_move = True

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
    ctx.search_message      = False
    ctx.search_note_content = False
    ctx.search_dict         = False
    ctx.search_tool         = True
    ctx.user_name           = user_name

    if category == "message":
        ctx.search_message = True
        ctx.search_note = False
        ctx.search_note_content = False
        ctx.search_tool = False

    if ctx.category == "book":
        ctx.search_note = False
        ctx.search_tool = False

    if category == "dict":
        ctx.search_dict = True
        ctx.search_note = False
        ctx.search_tool = False

    if category == "content":
        ctx.search_note_content = True
        ctx.search_tool         = False

    if category == "tool":
        ctx.search_tool = True

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

class SearchHandler:

    def do_search(self, page_ctx, key, offset, limit):
        category    = xutils.get_argument("category", "")
        search_type = xutils.get_argument("search_type", "")
        words      = textutil.split_words(key)
        user_name  = xauth.get_current_name()
        ctx        = build_search_context(user_name, category, key)

        # 优先使用 search_type
        if search_type != None and search_type != "" and search_type != "default":
            return self.do_search_by_type(page_ctx, key, search_type)
        
        # 阻断性的搜索，比如特定语法的
        xmanager.fire("search.before", ctx)
        if ctx.stop:
            files = ctx.join_as_files()
            return files, len(files)

        # 普通的搜索行为
        xmanager.fire("search", ctx)

        ctx.files = apply_search_rules(ctx, key)

        if ctx.stop:
            files = ctx.join_as_files()
            return files, len(files)

        # 慢搜索,如果时间过长,这个服务会被降级
        xmanager.fire("search.slow", ctx)
        xmanager.fire("search.after", ctx)

        page_ctx.tools = []
        
        search_result = ctx.join_as_files()
        
        fill_note_info(search_result)

        return search_result[offset:offset+limit], len(search_result)

    def do_search_with_profile(self, page_ctx, key, offset, limit):
        user_name = xauth.current_name()
        category  = xutils.get_argument("category", "")
        search_type = xutils.get_argument("search_type", "")

        start_time = time.time()

        result = self.do_search(page_ctx, key, offset, limit)

        cost_time = int((time.time() - start_time) * 1000)

        if category is None:
            category = search_type

        log_search_history(user_name, key, category, cost_time)

        return result

    def do_search_dict(self, ctx, key):
        offset = ctx.offset
        limit  = ctx.limit
        notes, count = DICT_DAO.search(key, offset, limit)
        for note in notes:
            note.raw = note.value
            note.icon = "hide"
        return notes, count

    def do_search_note(self, ctx, key):
        user_name = xauth.get_current_name()
        parent_id = xutils.get_argument("parent_id")
        words = textutil.split_words(key)
        notes = NOTE_DAO.search_name(words, user_name, parent_id = parent_id)
        for note in notes:
            note.category = "note"
            note.mdate = dateutil.format_date(note.mtime)
        fill_note_info(notes)

        if parent_id != "" and parent_id != None:
            ctx.parent_note = NOTE_DAO.get_by_id(parent_id)

        offset = ctx.offset
        limit  = ctx.limit
        return notes[offset:offset+limit], len(notes)

    def do_search_task(self, ctx, key):
        user_name = xauth.get_current_name()
        offset = ctx.offset
        limit  = ctx.limit

        search_tags = set(["task", "done"])
        item_list, amount = MSG_DAO.search(user_name, key, offset, limit, search_tags = search_tags)

        for item in item_list:
            MSG_DAO.process_message(item)
            prefix = u("待办 - ")

            if item.tag == "done":
                prefix = u("完成 - ")

            item.name = prefix + item.ctime
            item.icon = "hide"
            item.url  = "#"

        return item_list, amount


    def do_search_by_type(self, ctx, key, search_type):
        if search_type == "note":
            return self.do_search_note(ctx, key)
        elif search_type == "dict":
            return self.do_search_dict(ctx, key)
        elif search_type == "task":
            return self.do_search_task(ctx, key)
        else:
            raise Exception("不支持的搜索类型:%s" % search_type)

    def GET(self, path_key = None):
        """search files by name and content"""
        load_rules()
        key       = xutils.get_argument("key", "")
        title     = xutils.get_argument("title", "")
        category  = xutils.get_argument("category", "default")
        page      = xutils.get_argument("page", 1, type = int)
        search_type = xutils.get_argument("search_type", "")
        user_name = xauth.get_current_name()
        page_url  =  "/search/search?key={key}&category={category}&search_type={search_type}&page=".format(**locals())
        pagesize = xconfig.SEARCH_PAGE_SIZE
        offset   = (page-1) * pagesize
        limit    = pagesize
        ctx      = Storage()
        ctx.offset = offset
        ctx.limit  = limit

        if path_key:
            key = xutils.unquote(path_key)

        if key == "" or key == None:
            raise web.found("/search/history")

        key = key.strip()

        files, count = self.do_search_with_profile(ctx, key, offset, pagesize)

        return xtemplate.render("search/page/search_result.html", 
            show_aside = False,
            key = key,
            html_title = "Search",
            category = category,
            files    = files, 
            title    = title,
            page_max = int(math.ceil(count/pagesize)),
            page_url = page_url,
            **ctx)


class SearchHistoryHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        xmanager.add_visit_log(user_name, "/search/history")
        return xtemplate.render("search/page/search_history.html", 
            show_aside = False,
            recent = list_search_history(user_name),
            html_title = "Search",
            files = [],
            search_tpye = "note")

rules_loaded = False
def load_rules():
    global rules_loaded
    if rules_loaded:
        return
    add_rule(r"([^ ]*)",  "api.search")
    add_rule(r"静音(.*)", "mute.search")
    add_rule(r"mute(.*)", "mute.search")
    add_rule(r"取消静音",  "mute.cancel")
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


@xmanager.listen("sys.reload")
def reload_search(ctx = None):
    do_reload_search(ctx)

@xutils.log_deco("reload_search")
def do_reload_search(ctx = None):
    register_search_handler("plugin", placeholder = u"搜索插件", action = "/plugins_list")
    register_search_handler("note.public", placeholder = u"搜索公共笔记", action = "/note/timeline", tag = "public")
    register_search_handler("dict", placeholder = u"搜索词典", action = "/search")
    register_search_handler("message", placeholder = u"搜索随手记", action = "/message")
    register_search_handler("task", placeholder = u"搜索待办", action = "/search")
    register_search_handler("note", placeholder = u"搜索笔记", action = "/search")
    register_search_handler("default", placeholder = u"综合搜索", action = "/search")


xutils.register_func("search.list_rules", list_search_rules)
xutils.register_func("search.list_recent", list_search_history)
xutils.register_func("search.get_search_handler", get_search_handler)

xurls = (
    r"/search/search", SearchHandler, 
    r"/search"       , SearchHandler,
    r"/s/(.+)"       , SearchHandler,
    r"/search/history", SearchHistoryHandler,
    r"/search/rules", RulesHandler,
)

