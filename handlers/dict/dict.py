# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/02/15 21:46:37
# @modified 2020/02/04 11:35:51
import xtables
import xtemplate
import xutils
import xauth
import xconfig
import math
from xutils import Storage

PAGE_SIZE = xconfig.PAGE_SIZE

SEARCH_KEYWORDS = dict(
    search_action = "/dict/search?key=",
    search_placeholder = "搜索词典",
)

def search_escape(text):
    if not (isinstance(text, str) or isinstance(text, unicode)):
        return text
    text = text.replace('/', '//')
    text = text.replace("'", '\'\'')
    text = text.replace('[', '/[')
    text = text.replace(']', '/]')
    #text = text.replace('%', '/%')
    #text = text.replace('&', '/&')
    #text = text.replace('_', '/_')
    text = text.replace('(', '/(')
    text = text.replace(')', '/)')
    return "'%" + text + "%'"

def convert_dict_func(item):
    v = Storage()
    v.name = item.key
    v.value = item.value
    v.summary = item.value
    v.mtime = item.mtime
    v.ctime = item.ctime
    v.url = "/dict/edit/%s" % item.key
    v.priority = 0
    v.show_next = True
    return v

class DictEditHandler:

    def GET(self, name=""):
        if name is None:
            name = ""
        name  = xutils.unquote(name)
        table = xtables.get_dict_table()
        item  = table.select_first(where=dict(key=name))
        value = ""
        if item != None:
            value = item.value
        return xtemplate.render("dict/dict_edit.html", 
            name = name, value = value, **SEARCH_KEYWORDS)

    @xauth.login_required("admin")
    def POST(self, name=""):
        key   = xutils.get_argument("name", "")
        value = xutils.get_argument("value", "")
        if key != "" and value != "":
            key   = xutils.unquote(key)
            table = xtables.get_dict_table()
            item  = table.select_first(where=dict(key=key))
            if item != None:
                table.update(value = value, where = dict(key = key))
            else:
                table.insert(key = key, value = value)
        return self.GET(name)

class DictSearchHandler:

    def GET(self):
        key  = xutils.get_argument("key")
        page = xutils.get_argument("page", 1, type=int)
        db   = xtables.get_dict_table()
        where_sql = "key LIKE %s" % search_escape(key)
        items = db.select(order="key", where = where_sql, limit=PAGE_SIZE, offset=(page-1)*PAGE_SIZE)
        items = map(convert_dict_func, items)
        count = db.count(where = where_sql)
        page_max = math.ceil(count / PAGE_SIZE)

        return xtemplate.render("dict/dict_list.html", 
            show_aside = True,
            files      = list(items), 
            file_type  = "group",
            show_opts  = False,
            page       = page,
            page_max   = page_max,
            pathlist   = [Storage(name = "词典", url = "#")],
            show_pagination = True,
            page_url   = "/note/dict?page=", 
            **SEARCH_KEYWORDS)


class DictHandler:

    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_dict_table()
        items = db.select(order="id", limit=PAGE_SIZE, offset=(page-1)*PAGE_SIZE)
        items = map(convert_dict_func, items)
        count = db.count()
        page_max = math.ceil(count / PAGE_SIZE)

        return xtemplate.render("dict/dict_list.html", 
            show_aside = True,
            files      = list(items), 
            file_type  = "group",
            show_opts  = False,
            page       = page,
            page_max   = page_max,
            pathlist   = [Storage(name = "词典", url = "#")],
            show_pagination = True,
            page_url   = "/note/dict?page=",
            **SEARCH_KEYWORDS)

xurls = (
    r"/dict/edit/(.+)", DictEditHandler,
    r"/dict/search",    DictSearchHandler,
    r"/note/dict",      DictHandler,
)