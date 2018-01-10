# encoding=utf-8
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
from xutils import Queue

config = xconfig

_rules = []

class History:

    def __init__(self, size):
        self.q = Queue()
        self.size = size

    def put(self, item):
        self.q.put(item)
        if self.q.qsize() > self.size:
            self.q.get()

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
        self.search_message = False
        self.search_file = True
        self.search_file_full = False
        self.user_name = ''

class handler:

    def full_search(self, key, offset, limit):
        global _rules
        content = xutils.get_argument("content")
        message = xutils.get_argument("message")
        words   = textutil.split_words(key)
        files   = []

        start_time = time.time()
        ctx = SearchContext()
        ctx.search_message = (message == "on")
        ctx.search_file_full = (content == "on")
        ctx.user_name = xauth.get_current_name()

        if ctx.search_message:
            ctx.search_file = False
            ctx.search_file_full = False

        xutils.log("  key=%s" % key)
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
                    xutils.print_stacktrace()
        cost_time = (time.time() - start_time) * 1000
        xutils.log("  === total - %d ms ===" % cost_time)
        return files

    def json_request(self):
        key = xutils.get_argument("key", "").strip()
        if key == "":
            raise web.seeother("/")
        return self.full_search(key, offset, limit)


    @xauth.login_required()
    def GET(self):
        """search files by name and content"""
        load_rules()
        key       = xutils.get_argument("key", "")
        title     = xutils.get_argument("title", "")
        content   = xutils.get_argument("content", "")
        message   = xutils.get_argument("message", "")
        page      = xutils.get_argument("page", 1, type = int)
        user_name = xauth.get_current_role()

        xutils.get_argument("page_url", "/search/search?key=%s&content=%s&message=%s&page="\
            % (key, content, message))
        pagesize = config.PAGE_SIZE
        offset   = (page-1) * pagesize
        limit    = pagesize

        if key == "" or key == None:
            return xtemplate.render("search_result.html", files=[], count=0)
        files = self.full_search(key, offset, pagesize)
        # TODO 待优化
        count = len(files)
        files = files[offset:offset+limit]
        return xtemplate.render("search_result.html", 
            files = files, 
            title = title,
            page_max = math.ceil(count/pagesize),
            content = content)

rules_loaded = False
def load_rules():
    global rules_loaded
    if rules_loaded:
        return
    add_rule(r"(.*[0-9]+.*)",           "calc.do_calc")
    add_rule(r"([a-zA-Z0-9\.]*)",       "pydoc.search")
    add_rule(r"([a-zA-Z\-]*)",          "translate.search")
    add_rule(r"翻译\s+([^ ]+)",         "translate.zh2en")
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
    add_rule(r"(.*)", "file.search")
    rules_loaded = True

xurls = (
    r"/search/search", handler, 
    r"/search", handler
)

