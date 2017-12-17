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
        xutils.print_stacktrace()


class StoreItem:

    def __init__(self, timeout, data):
        self.timeout = timeout
        self.data = data

class MemStore(web.session.DiskStore):
    """内存型的存储,用来缓存搜索结果"""

    # 存储结构，静态的dict
    item_cache = dict()

    def __init__(self):
        pass

    def __getitem__(self, key):
        return self.item_cache[key].data

    def __setitem__(self, key, value):
        # 删除失效的搜索结果
        self.clear_timeout_items()
        self.item_cache[key] = StoreItem(time.time() + 60, value)

    def __delitem__(self, key):
        del self.item_cache[key]

    def __contains__(self, key):
        return key in self.item_cache

    def encode(self, session_dict):
        """encodes session dict as a string"""
        # pickled = json.dumps(session_dict).encode("utf-8")
        # return base64.encodestring(pickled)
        return json.dumps(session_dict).encode("utf-8")

    def decode(self, session_data):
        """decodes the data to get back the session dict """
        # pickled = base64.decodestring(session_data).decode("utf-8")
        # return json.loads(pickled)
        return json.loads(session_data.decode("utf-8"))

    def clear_timeout_items(self):
        for key in list(self.item_cache.keys()):
            self.has_key(key)

    def has_key(self, key):
        # 判断key是否存在
        # print(self.item_cache)
        if key in self.item_cache:
            item = self.item_cache[key]
            if item.timeout > time.time():
                return True
            else:
                # 清除失效的缓存
                # print("DEL %s" % key)
                del self.item_cache[key]
                return False
        return False

    def load_from_file(self, key):
        # print("hit cache %s" % key)
        files = self[key].data
        for i, f in enumerate(files):
            f = FileDO.fromDict(f)
            files[i] = f
        return files

    def store_search_result(self, files):
        # if full_search == "on":
        #     return self.full_search();
        def map_func(data):
            for k in data:
                if data[k] is None:
                    data[k] = ""
            if "content" in data:
                data["content"] = data["content"][:100]
            return data
        values = list(map(map_func , files))
        self[store_key] = values 

class handler:

    store = MemStore()
    def full_search(self, key, offset, limit):
        global _rules
        words = textutil.split_words(key)
        files = []
        start_time = time.time()
        for rule in _rules:
            pattern = rule.pattern
            func = rule.func
            # re.match内部已经实现了缓存
            m = re.match(pattern, key)
            if m:
                try:
                    start_time0 = time.time()
                    results = func(*m.groups())
                    cost_time0 = time.time() - start_time0
                    print("  >>> %s - %d ms" % (func.modfunc, cost_time0*1000))
                    if results is not None:
                        files += results
                except Exception as e:
                    xutils.print_stacktrace()
        cost_time = (time.time() - start_time) * 1000
        print("  === total - %d ms ===" % cost_time)
        return files

    def json_request(self):
        key = xutils.get_argument("key", "").strip()
        if key == "":
            raise web.seeother("/")
        return self.full_search(key, offset, limit)


    @xauth.login_required()
    def GET(self):
        """search files by name and content"""
        if not rules_loaded:
            load_rules()
        key  = xutils.get_argument("key", "")
        title = xutils.get_argument("title", "")
        content = xutils.get_argument("content", "")
        page = xutils.get_argument("page", 1, type = int)
        user_name = xauth.get_current_role()
        xutils.get_argument("page_url", "/search/search?key=%s&content=%s&page=" % (key, content))
        pagesize = config.PAGE_SIZE
        offset = (page-1) * pagesize
        limit  = pagesize

        if key == "" or key == None:
            return xtemplate.render("search_result.html", files=[], count=0)
        # app 为None，不用全局使用session
        store = self.store
        store_key = "s_" + user_name + "-" + key
        # print("STORE KEY: ", store_key)
        if store.has_key(store_key):
            # print("HIT %s" % store_key)
            files = store[store_key]
        else:
            files = self.full_search(key, offset, pagesize)
            # store[store_key] = files
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
    add_rule(r"(.*)",                   "file.search")
    rules_loaded = True

xurls = (
    r"/search/search", handler, 
    r"/search", handler
)

