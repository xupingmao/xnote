# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/02/15 21:46:37
# @modified 2022/04/18 23:25:56
import xtables
import xtemplate
import xutils
import xauth
import xconfig
import xmanager
import math
from xutils import Storage, encode_uri_component, dateutil
from xutils.imports import is_str

from . import dict_dao

PAGE_SIZE = xconfig.PAGE_SIZE

def escape_sqlite_text(text):
    text = text.replace('/', '//')
    text = text.replace("'", '\'\'')
    text = text.replace('[', '/[')
    text = text.replace(']', '/]')
    text = text.replace('(', '/(')
    text = text.replace(')', '/)')
    return text

def search_escape(text):
    if not is_str(text):
        return text
    text = escape_sqlite_text(text)
    return "'%" + text + "%'"

def left_match_escape(text):
    return "'%s%%'" % escape_sqlite_text(text)


def convert_dict_func(item):
    v = Storage()
    v.name = item.key
    v.value = item.value
    v.summary = item.value
    v.mtime = item.mtime
    v.ctime = item.ctime
    v.url = "/dict/update?id=%s" % item.id
    v.priority = 0
    v.show_next = True
    return v

def search_dict(key, offset = 0, limit = None):
    if limit is None:
        limit = PAGE_SIZE
    db = xtables.get_dict_table()
    where_sql = "key LIKE %s" % left_match_escape(key)
    items = db.select(order="key", where = where_sql, limit=limit, offset=offset)
    items = list(map(convert_dict_func, items))
    count = db.count(where = where_sql)
    return items, count


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
        return xtemplate.render("dict/page/dict_edit.html", 
            name = name, value = value, search_type = "dict")

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
        items, count = search_dict(key, (page-1) * PAGE_SIZE)
        page_max = math.ceil(count / PAGE_SIZE)

        return xtemplate.render("dict/page/dict_list.html", 
            show_aside = True,
            files      = items, 
            file_type  = "group",
            show_opts  = False,
            page       = page,
            page_max   = page_max,
            show_pagination = True,
            page_url   = "/dict/search?key=%s&page=" % encode_uri_component(key), 
            search_type = "dict")


class DictHandler:

    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_dict_table()
        items = db.select(order="id", limit=PAGE_SIZE, offset=(page-1)*PAGE_SIZE)
        items = map(convert_dict_func, items)
        count = db.count()
        page_max = math.ceil(count / PAGE_SIZE)

        user_name = xauth.current_name()
        xmanager.add_visit_log(user_name, "/note/dict")

        return xtemplate.render("dict/page/dict_list.html", 
            show_aside = True,
            files      = list(items), 
            file_type  = "group",
            show_opts  = False,
            page       = page,
            page_max   = page_max,
            pathlist   = [Storage(name = "词典", url = "#")],
            show_pagination = True,
            page_url   = "/note/dict?page=",
            search_type = "dict")

class DictAddHandler:

    @xauth.login_required("admin")
    def GET(self):
        return xtemplate.render("dict/page/dict_add.html")

class DictUpdateHandler:

    @xauth.login_required()
    def GET(self):
        item_id = xutils.get_argument_int("id")
        item = dict_dao.get_by_id(item_id)
        kw = Storage()
        if item != None:
            kw.name = item.key
            kw.value = item.value
        return xtemplate.render("dict/page/dict_update.html", **kw)

class CreateAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        key = xutils.get_argument_str("key", "")
        value = xutils.get_argument_str("value", "")
        if key == "":
            return dict(code="400", message="key不能为空")

        if value == "":
            return dict(code="400", message="value不能为空")

        key   = xutils.unquote(key)
        table = xtables.get_dict_table()
        item  = table.select_first(where=dict(key=key))
        if item != None:
            return dict(code="302", message="记录已经存在，请前往更新", data = dict(url = "/dict/update?id=%s" % item.id))
        else:
            new_record = dict_dao.DictItem()
            new_record.key = key
            new_record.value = value
            new_record.ctime = dateutil.format_datetime()
            new_record.mtime = dateutil.format_datetime()
            id = dict_dao.create(new_record)
            return dict(code="success", data = dict(url = "/dict/update?id=%s" % id))


class UpdateAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        id = xutils.get_argument_int("id")
        value = xutils.get_argument_str("value")
        dict_dao.update(id, value)
        return dict(code="success")


class DeleteAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        id = xutils.get_argument_int("id")
        dict_dao.delete(id)
        return dict(code="success")

xutils.register_func("dict.search", search_dict)

xurls = (
    r"/dict/add", DictAddHandler,
    r"/dict/edit/(.+)", DictEditHandler,
    r"/dict/update",    DictUpdateHandler,
    r"/dict/search",    DictSearchHandler,
    r"/dict/list",      DictHandler,
    r"/note/dict",      DictHandler,

    r"/api/dict/create", CreateAjaxHandler,
    r"/api/dict/update", UpdateAjaxHandler,
    r"/api/dict/delete", DeleteAjaxHandler,
)