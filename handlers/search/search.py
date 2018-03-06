# encoding=utf-8
# @author xupingmao
# @modified 2018/03/06 23:30:05

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
from util import textutil
from xutils import Queue, History

config = xconfig

_rules = []

class BaseRule:

    def __init__(self, pattern, func, scope="home"):
        self.pattern = pattern
        self.func = func
        self.scope = scope

def add_rule(pattern, func_str):
    global _rules
    try:
        mod, func_name = func_str.rsplit('.', 1)
        # mod = __import__(mod, None, None, [''])
        mod = six._import_module("handlers.search." + mod)
        func = getattr(mod, func_name)
        func.modfunc = func_str
        rule = BaseRule(r"^%s\Z" % pattern, func)
        _rules.append(rule)
    except Exception as e:
        xutils.print_exc()

class SearchContext:

    def __init__(self):
        # 输入的文本
        self.input_text = ''
        self.user_name = ''

        self.search_message = False
        self.search_file = True
        self.search_file_full = False
        self.search_dict = False
        self.search_tool = True
        
        # 处理的结果集
        self.tools = []
        self.notes = []
        self.dict_files = []
        self.message_files = []

class handler:
    xconfig.search_history = History("搜索记录", 200)

    def do_search(self, key, offset, limit):
        global _rules

        category = xutils.get_argument("category", "")
        words   = textutil.split_words(key)
        files   = []
        xconfig.search_history.put(dict(key=key, category=category, user=xauth.get_current_name()))

        start_time = time.time()
        ctx = SearchContext()
        ctx.input_text = key
        ctx.words = words
        ctx.category = category
        ctx.search_message = (category == "message")
        ctx.search_file_full = (category == "content")
        ctx.search_dict = (category == "dict")
        ctx.user_name = xauth.get_current_name()

        if ctx.search_message:
            ctx.search_file = False
            ctx.search_file_full = False
            ctx.search_tool = False
        if ctx.search_dict:
            ctx.search_file = False
        if ctx.search_file_full:
            ctx.search_tool = False

        xutils.log("  key=%s" % key)

        xmanager.fire("search.before", ctx)
        xmanager.fire("search", ctx)

        for rule in _rules:
            pattern = rule.pattern
            func = rule.func
            # re.match内部已经实现了缓存
            m = re.match(pattern, key)
            if m:
                try:
                    start_time0 = time.time()
                    results = func(ctx, *m.groups())
                    cost_time0 = time.time() - start_time0
                    xutils.log("  >>> %s - %d ms" % (func.modfunc, cost_time0*1000))
                    if results is not None:
                        files += results
                except Exception as e:
                    xutils.print_exc()
        cost_time = (time.time() - start_time) * 1000
        xutils.log("  === total - %d ms ===" % cost_time)
        xmanager.fire("search.after", ctx)
        return ctx.tools + files

    @xauth.login_required()
    def GET(self):
        """search files by name and content"""
        load_rules()
        key       = xutils.get_argument("key", "")
        title     = xutils.get_argument("title", "")
        category  = xutils.get_argument("category", "")
        page      = xutils.get_argument("page", 1, type = int)
        user_name = xauth.get_current_role()
        page_url  =  "/search/search?key=%s&category=%s&page="\
            % (key, category)
        pagesize = xconfig.PAGE_SIZE
        offset   = (page-1) * pagesize
        limit    = pagesize

        if key == "" or key == None:
            return xtemplate.render("search_result.html", category=category, files=[], count=0)
        files = self.do_search(key, offset, pagesize)
        count = len(files)
        files = files[offset:offset+limit]
        return xtemplate.render("search_result.html", 
            category = category,
            files = files, 
            title = title,
            page_max = math.ceil(count/pagesize),
            page_url = page_url)

rules_loaded = False
def load_rules():
    global rules_loaded
    if rules_loaded:
        return
    add_rule(r"(.*[0-9]+.*)",           "calc.do_calc")
    add_rule(r"([a-zA-Z0-9\.]+)",       "pydoc.search")
    add_rule(r"翻译\s+([^ ]+)",         "dictionary.zh2en")
    add_rule(r"[a-zA-Z\-]+", "dictionary.find")
    add_rule(r"([^ ]*)",                "tools.search")
    add_rule(r"([^ ]*)",                "scripts.search")
    add_rule(r"([^ ]*)",                "api.search")
    add_rule(r"(\d+)分钟后提醒我?(.*)", "reminder.search")
    add_rule(r"(上午|下午)(.*)提醒我?(.*)", "reminder.by_time")
    add_rule(r"(.*)日提醒我?(.*)","reminder.by_date")
    add_rule(r"静音(.*)",               "mute.search")
    add_rule(r"mute(.*)",               "mute.search")
    add_rule(r"取消静音",               "mute.cancel")
    add_rule(r"(.*)", "message.search")
    add_rule(r"(.*)", "note.search")
    rules_loaded = True

xurls = (
    r"/search/search", handler, 
    r"/search", handler
)

