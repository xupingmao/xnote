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

config = xconfig

_mappings = []

def load_mapping(pattern, func_str):
    global _mappings
    try:
        mod, func_name = func_str.rsplit('.', 1)
        # mod = __import__(mod, None, None, [''])
        mod = six._import_module("handlers.search." + mod)
        func = getattr(mod, func_name)
        func.modfunc = func_str
        _mappings.append(r"^%s\Z" % pattern)
        _mappings.append(func)
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

    def _match(self, key):
        global _mappings
        mappings = _mappings
        for i in range(0, len(mappings), 2):
            pattern = mappings[i]
            func = mappings[i+1]
            m = re.match(pattern, key)
            if m:
                return func, m.groups()
        return None, None


    def full_search(self, key, offset, limit):
        global _mappings
        mappings = _mappings
        words = textutil.split_words(key)
        files = []
        for i in range(0, len(mappings), 2):
            pattern = mappings[i]
            func = mappings[i+1]
            m = re.match(pattern, key)
            if m:
                try:
                    print("  >>> ", func.modfunc)
                    results = func(*m.groups())
                    if results is not None:
                        files += results
                except Exception as e:
                    xutils.print_stacktrace()
        return files

    def json_request(self):
        key = xutils.get_argument("key", "").strip()
        if key == "":
            raise web.seeother("/")
        return self.full_search(key, offset, limit)


    @xauth.login_required()
    def GET(self):
        """search files by name and content"""
        if not mappings_loaded:
            load_mappings()
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
            return xtemplate.render("search-result.html", files=[], count=0)
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
        files = files[offset:offset+limit]
        count = len(files)
        return xtemplate.render("search-result.html", 
            files = files, 
            count = count,
            title = title,
            content = content)

mappings_loaded = False
def load_mappings():
    global mappings_loaded
    load_mapping(r"(.*[0-9]+.*)",           "calc.do_calc")
    load_mapping(r"([a-zA-Z0-9\.]*)",       "pydoc.search")
    load_mapping(r"([a-zA-Z\-]*)",          "translate.search")
    load_mapping(r"翻译\s+([^ ]+)",         "translate.zh2en")
    load_mapping(r"([^ ]*)",                "tools.search")
    load_mapping(r"([^ ]*)",                "scripts.search")
    load_mapping(r"([^ ]*)",                "api.search")
    load_mapping(r"(\d+)分钟后提醒我?(.*)", "reminder.search")
    load_mapping(r"静音(.*)",               "mute.search")
    load_mapping(r"mute(.*)",               "mute.search")
    load_mapping(r"取消静音",               "mute.cancel")
    load_mapping(r"(.*)",                   "file.search")
    mappings_loaded = True

xurls = (
    r"/search/search", handler, 
    r"/search", handler
)

