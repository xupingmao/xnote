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
from xnote_handlers.dict.dict_dao import search_dict, convert_dict_func
from xnote_handlers.note.models import NoteTypeInfo
from .models import DictTypeEnum, DictTypeItem
from xnote.plugin.table import DataTable
from xnote.plugin.table_plugin import BaseTablePlugin, TableActionType, FormRowType
from xnote.plugin.list_plugin import BaseListPlugin
from xnote.plugin.form import DataForm, QueryForm, PageEditForm
from xnote_handlers.config import LinkConfig
from xnote.webui import ListViewItem, EditFormActionLink

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

def can_edit_dict(dict_type=0):
    """检查是否能编辑, admin可以编辑所有词典, 普通用户只能编辑个人词典"""
    if dict_type == 0:
        dict_type = xutils.get_argument_int("dict_type")
    enum_item = DictTypeEnum.get_by_int_value(dict_type)
    assert enum_item != None
    if enum_item.has_user_id:
        return True
    return xauth.is_admin()
        
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

class DictHandler(BaseListPlugin):

    title = "词典"
    show_aside = True
    dict_type = ""
    search_type = "dict"
    search_placeholder = "搜索词典"
    search_action = "/note/dict"
    permitted_role_list = ["user", "admin"]

    PAGE_HTML = """
{% include note/component/filter/type_filter.html %}
{% include dict/page/dict_type_tab.html %}
""" + BaseListPlugin.page_html
    
    page_edit_html = """
<div class="card">
    {% render dict_form %}
</div>
"""

    page_edit_no_auth_html = """
<div class="form-row">
    <label>&nbsp;</label>
    <span>无编辑权限</span>
</div>
"""
        
    def get_page_html(self):
        return self.PAGE_HTML
    
    def get_aside_html(self):
        if DictHandler.aside_html != "":
            return DictHandler.aside_html
        DictHandler.aside_html = xtemplate.render_text("{% include dict/page/dict_sidebar.html %}")
        return DictHandler.aside_html
    
    def get_option_html(self):
        if self.dict_type == "":
            return ""
        
        server_home = xconfig.WebConfig.server_home
        return f"""
<a class="btn btn-default" href="{server_home}/dict/list?action=page_edit&dict_type={self.dict_type}">新增</a>
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

        list_view = self.create_list_view()

        for item in items:
            list_item = ListViewItem()
            list_item.add_link(text=item.key, href=item.url, css_class="bold")
            list_item.add_br()
            list_item.add_span(textutil.get_short_text(item.value, 100), css_class="gray")
            edit_url = f"?action=edit&dict_type={item.dict_type}&dict_id={item.dict_id}"
            
            if self.show_edit_action():
                list_item.extra.add(EditFormActionLink(text="编辑", url=edit_url))
            
            list_view.add(list_item)

        kw = Storage()
        kw.type_list = NoteTypeInfo.get_type_list()
        kw.note_type = "dict"
        kw.page_url = f"/note/dict?dict_type={dict_type}&page="
        kw.show_pagination = True
        kw.page_max   = page_max
        kw.page       = page
        kw.file_type  = "group"
        kw.list_view = list_view

        self.search_action = f"/note/dict?dict_type={dict_type}"

        return self.response_page(**kw)
    
    def handle_page_edit(self):
        dict_id = xutils.get_argument_int("dict_id")
        dict_type = self.get_dict_type()
        dao = self.get_dict_dao()
        user_id = xauth.current_user_id()
        if dict_id > 0:
            item = dao.get_by_id(dict_id, user_id=user_id)
        else:
            item = dict_dao.DictDO()

        if item == None:
            return self.response_text("dict_item is None")
        
        self.parent_link = LinkConfig.dict_list
        self.title = "编辑"

        dict_form = PageEditForm()
        dict_form.delete_reload_href = xconfig.WebConfig.resolve_path(f"/dict/list?dict_type={dict_type}")
        dict_form.delete_confirm_msg = f"确认删除记录[{item.key}]吗?"
        dict_form.delete_url = f"?action=delete&dict_id={item.dict_id}"

        dict_form.add_row(field="dict_id", value=str(item.dict_id), css_class="hide")
        row = dict_form.add_select(title="类型", field="dict_type", value=str(item.dict_type))
        for type_info in DictTypeEnum.enums():
            row.add_option(title=type_info.name, value=type_info.value)

        dict_form.add_row(title="名称", field="key", value=item.key)
        dict_form.add_textarea(title="解释", field="value", value=item.value)

        if not can_edit_dict(dict_type):
            dict_form.footer_html = self.page_edit_no_auth_html

        self.writetemplate(self.page_edit_html, dict_form = dict_form)
    
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
        dict_type_name = DictTypeEnum.get_name_by_value(str(dict_type))
        form.add_row("词典类型", "dict_type", type=FormRowType.input, value=dict_type_name, readonly=True)
        form.add_row("关键字", "key", value=dict_item.key, readonly=True)
        form.add_row("解释", "value", type=FormRowType.textarea, value=dict_item.value)
        if dict_type == DictTypeEnum.relevant.int_value:
            form.add_row("说明", type=FormRowType.textarea, value="多个单词使用空格或者换行分隔", readonly=True)
        
        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def handle_save(self):
        data_dict = self.get_data_dict()
        dict_type = data_dict.get_int("dict_type")
        check_edit_auth(dict_type=dict_type)
        dict_id = data_dict.get_int("dict_id")
        key = data_dict.get_str("key")
        value = data_dict.get_str("value")
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
            dict_item.dict_type = dict_type
            dao.create(dict_item)
        else:
            dao.update(dict_id=dict_id, user_id=user_id, value=value)
        return webutil.SuccessResult()
    
    def handle_delete(self):
        dict_id = xutils.get_argument_int("dict_id")
        user_id = xauth.current_user_id()
        record = dict_dao.DictPublicDao.get_by_id(dict_id=dict_id, user_id=user_id, ignore_type=True)
        if record is None:
            return webutil.FailedResult("404", message="record not found")
        dict_dao.DictPublicDao.delete_by_id(dict_id=dict_id)
        return webutil.SuccessResult()

    
class DictAddHandler(BaseDictHandler):

    @xauth.login_required()
    def GET(self):
        dict_type = self.get_dict_type()
        if dict_type == DictTypeEnum.public.value:
            xauth.check_login("admin")
        kw = self.create_kw()
        return xtemplate.render("dict/page/dict_add.html", **kw)


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
    r"/dict/search",    DictHandler,
    r"/dict/list",      DictHandler,
    r"/note/dict",      DictHandler,

    r"/api/dict/create", CreateAjaxHandler,
    r"/api/dict/update", UpdateAjaxHandler,
    r"/api/dict/delete", DeleteAjaxHandler,
)