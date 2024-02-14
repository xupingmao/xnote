# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/02/15 21:46:37
# @modified 2022/04/18 23:25:56

from xnote.core import xtables
from xnote.core import xtemplate
import xutils
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xmanager
import math
from xutils import Storage, encode_uri_component, dateutil

from . import dict_dao
from handlers.dict.dict_dao import search_dict, convert_dict_func

PAGE_SIZE = xconfig.PAGE_SIZE

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
        page = xutils.get_argument_int("page", 1)
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
        page = xutils.get_argument_int("page", 1)
        db = xtables.get_dict_table()
        items = db.select(order="id", limit=PAGE_SIZE, offset=(page-1)*PAGE_SIZE)
        items = map(convert_dict_func, items)
        count = db.count()
        page_max = math.ceil(count / PAGE_SIZE)

        user_name = xauth.current_name_str()
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
        item  = dict_dao.get_by_key(key)
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