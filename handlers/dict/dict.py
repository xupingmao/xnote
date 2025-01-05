# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/02/15 21:46:37
# @modified 2022/04/18 23:25:56

import math
import xutils

from xnote.core import xtables
from xnote.core import xtemplate
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xmanager
from xutils import Storage, encode_uri_component, dateutil
from xutils import webutil
from xutils import textutil

from . import dict_dao
from handlers.dict.dict_dao import search_dict, convert_dict_func
from handlers.note.models import NoteTypeInfo
from .models import DictTypeEnum, DictTypeItem
from xnote.plugin.table import DataTable
from xnote.plugin.table_plugin import BaseTablePlugin, TableActionType, FormRowType


PAGE_SIZE = xconfig.PAGE_SIZE

def check_edit_auth(dict_type=0):
    if dict_type == 0:
        dict_type = xutils.get_argument_int("dict_type")
    enum_item = DictTypeEnum.get_by_int_value(dict_type)
    assert enum_item != None
    if enum_item.has_user_id:
        xauth.check_login()
    else:
        xauth.check_login("admin")
        
class BaseDictHandler:

    def get_dict_type(self):
        return xutils.get_argument_int("dict_type", DictTypeEnum.get_default().int_value)
    
    def get_dict_dao(self):
        dict_type = self.get_dict_type()
        return dict_dao.get_dao_by_type(dict_type)
    
    def create_kw(self):
        can_edit = xauth.is_admin()
        dict_type = self.get_dict_type()
        if dict_type == DictTypeEnum.personal.int_value:
            can_edit = True

        kw = Storage()
        kw.dict_type = self.get_dict_type()
        kw.dict_type_str = DictTypeEnum.get_name_by_value(str(dict_type))
        kw.can_edit = can_edit
        return kw

class DictHandler(BaseTablePlugin):

    title = "词典"
    show_aside = True
    show_right = True
    dict_type = ""
    search_type = "dict"
    search_placeholder = "搜索词典"
    search_action = "/note/dict"
    permitted_role_list = ["user", "admin"]

    PAGE_HTML = """
{% include note/component/filter/type_filter.html %}
{% include dict/page/dict_type_tab.html %}
""" + BaseTablePlugin.TABLE_HTML
        
    def get_page_html(self):
        return self.PAGE_HTML
    
    def get_aside_html(self):
        if DictHandler.aside_html != "":
            return DictHandler.aside_html
        DictHandler.aside_html = xtemplate.render_text("{% include dict/page/dict_sidebar.html %}")
        return DictHandler.aside_html
    
    def get_option_html(self):
        server_home = xconfig.WebConfig.server_home
        return f"""
<a class="btn btn-default" href="{server_home}/dict/add?dict_type={self.dict_type}">新增</a>
"""
    
    def get_dict_type(self):
        return xutils.get_argument_int("dict_type")

    def get_dict_dao(self, dict_type=0):
        if dict_type == 0:
            dict_type = self.get_dict_type()
        return dict_dao.get_dao_by_type(dict_type)

    def show_edit_action(self):
        dict_type = self.get_dict_type()
        dict_type_info = DictTypeEnum.get_by_int_value(dict_type)
        if dict_type_info == None:
            return False
        if dict_type_info.has_user_id:
            return True
        return xauth.is_admin()

    def handle_page(self):
        dict_type = xutils.get_argument_int("dict_type", DictTypeEnum.get_default().int_value)
        fuzzy_key = xutils.get_argument_str("key")
        page = xutils.get_argument_int("page", 1)
        self.dict_type = dict_type

        user_id = xauth.current_user_id()
        limit=PAGE_SIZE
        offset=(page-1)*PAGE_SIZE

        dao = dict_dao.get_dao_by_type(dict_type)
        items, amount = dao.find_page(user_id=user_id, fuzzy_key=fuzzy_key, offset=offset, limit=limit)

        page_max = math.ceil(amount / PAGE_SIZE)
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, f"/note/dict?dict_type={dict_type}")

        table = DataTable()
        table.add_head("关键字", field="key", width="20%", link_field="view_url")
        table.add_head("解释", field="value", width="60%")

        if self.show_edit_action():
            table.add_action(title="编辑", type=TableActionType.edit_form, link_field="edit_url", css_class="btn btn-default")

        for item in items:
            item.view_url = item.url
            item.edit_url = f"?action=edit&dict_type={item.dict_type}&dict_id={item.dict_id}"
            item.value = textutil.get_short_text(item.value, 100)
            table.add_row(item)

        kw = Storage()
        kw.type_list = NoteTypeInfo.get_type_list()
        kw.note_type = "dict"
        kw.page_url = f"/note/dict?dict_type={dict_type}&page="
        kw.show_pagination = True
        kw.page_max   = page_max
        kw.page       = page
        kw.file_type  = "group"
        kw.table = table

        self.search_action = f"/note/dict?dict_type={dict_type}"

        return self.response_page(**kw)
    
    def handle_edit(self):
        check_edit_auth()
        dict_id = xutils.get_argument_int("dict_id")
        dict_type = self.get_dict_type()
        user_id = xauth.current_user_id()

        dao = self.get_dict_dao()
        if dict_id > 0:
            dict_item = dao.get_by_id(dict_id, user_id=user_id)
        else:
            dict_item = dict_dao.DictDO()

        if dict_item == None:
            return self.response_text("dict_item为空")

        form = self.create_form()
        form.add_row("dict_id", "dict_id", value=str(dict_item.dict_id), css_class="hide")

        row = form.add_row("词典类型", "dict_type", type=FormRowType.select, value=str(dict_type), readonly=True)

        for item in DictTypeEnum.enums():
            row.add_option(item.name, item.value)
        
        form.add_row("关键字", "key", value=dict_item.key, readonly=True)
        form.add_row("解释", "value", type=FormRowType.textarea, value=dict_item.value)
        
        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def handle_save(self):
        check_edit_auth()
        data_dict = self.get_data_dict()
        dict_id = data_dict.get_int("dict_id")
        key = data_dict.get_str("key")
        value = data_dict.get_str("value")
        dict_type = data_dict.get_int("dict_type")
        dao = self.get_dict_dao(dict_type)

        user_id = xauth.current_user_id()

        if dict_id == 0:
            # insert
            old = dao.find_one(user_id=user_id, key=key)
            if old is not None:
                return webutil.FailedResult("400", message=f"关键字【{key}】已存在")
            dict_item = dict_dao.DictDO()
            dict_item.key = key
            dict_item.value = value
            dict_item.user_id = user_id
            dao.create(dict_item)
        else:
            dao.update(dict_id=dict_id, user_id=user_id, value=value)
        return webutil.SuccessResult()
    
class DictAddHandler(BaseDictHandler):

    @xauth.login_required()
    def GET(self):
        dict_type = self.get_dict_type()
        if dict_type == DictTypeEnum.public.value:
            xauth.check_login("admin")
        kw = self.create_kw()
        return xtemplate.render("dict/page/dict_add.html", **kw)

class DictUpdateHandler(BaseDictHandler):

    @xauth.login_required()
    def GET(self):
        dict_id = xutils.get_argument_int("dict_id")
        dao = self.get_dict_dao()
        user_id = xauth.current_user_id()
        item = dao.get_by_id(dict_id, user_id=user_id)
        kw = self.create_kw()
        if item != None:
            kw.name = item.key
            kw.value = item.value
        return xtemplate.render("dict/page/dict_update.html", **kw)

class CreateAjaxHandler(BaseDictHandler):
    def POST(self):
        check_edit_auth()
        key = xutils.get_argument_str("key", "")
        value = xutils.get_argument_str("value", "")
        if key == "":
            return webutil.FailedResult(code="400", message="key不能为空")

        if value == "":
            return webutil.FailedResult(code="400", message="value不能为空")
        
        dao = self.get_dict_dao()
        user_id = xauth.current_user_id()
        item  = dao.find_one(user_id=user_id, key=key)
        if item != None:
            result = webutil.FailedResult(code="302", message="记录已经存在，请前往更新")
            result.data = dict(url = item.url)
            return result
        else:
            new_record = dict_dao.DictDO()
            new_record.key = key
            new_record.value = value
            new_record.user_id = user_id
            new_record.ctime = dateutil.format_datetime()
            new_record.mtime = dateutil.format_datetime()
            new_record.dict_type = self.get_dict_type()
            dao.create(new_record)
            return webutil.SuccessResult(data = dict(url = new_record.url))


class UpdateAjaxHandler(BaseDictHandler):

    def POST(self):
        check_edit_auth()
        dict_id = xutils.get_argument_int("dict_id")
        key = xutils.get_argument_str("key")
        value = xutils.get_argument_str("value")
        if dict_id <= 0:
            return webutil.FailedResult(code="400", message="无效的dict_id")
        dao = self.get_dict_dao()
        user_id = xauth.current_user_id()
        find_by_key = dao.find_one(user_id=user_id, key=key)
        if find_by_key is None:
            dao.update(dict_id=dict_id, user_id=user_id, key=key, value=value)
        elif find_by_key.dict_id == dict_id:
            dao.update(dict_id=dict_id, user_id=user_id, value=value)
        else:
            return webutil.FailedResult(code="500", message="关键字冲突")
        
        return webutil.SuccessResult()


class DeleteAjaxHandler(BaseDictHandler):

    def POST(self):
        check_edit_auth()
        dict_id = xutils.get_argument_int("dict_id")
        dao = self.get_dict_dao()
        dao.delete_by_id(dict_id)
        return webutil.SuccessResult()

xutils.register_func("dict.search", search_dict)

xurls = (
    r"/dict/add", DictAddHandler,
    r"/dict/update",    DictUpdateHandler,
    r"/dict/search",    DictHandler,
    r"/dict/list",      DictHandler,
    r"/note/dict",      DictHandler,

    r"/api/dict/create", CreateAjaxHandler,
    r"/api/dict/update", UpdateAjaxHandler,
    r"/api/dict/delete", DeleteAjaxHandler,
)