# encoding=utf-8

import xutils
from xutils import Storage
from xutils import webutil
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import FormRowType, TableActionType
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.service import TagInfoService, TagTypeEnum
from xnote.service import TagCategoryService, TagCategoryDO

class BaseTagManageHandler(BaseTablePlugin):
    require_admin = False
    require_login = True
    title = "标签管理"
    show_aside = True

    def get_aside_html(self):
        return xtemplate.render_text("""{% include note/component/sidebar/group_list_sidebar.html %}""")

class TagCategoryManageHandler(BaseTagManageHandler):

    PAGE_HTML = """
{% include note/page/taglist_tab.html %}
{% include note/page/taglist_subtab.html %}

<div class="card">
    <div class="table-action-row">
        <button class="btn" onclick="xnote.table.handleEditForm(this)"
            data-url="?action=edit" data-title="{{create_btn_text}}">{{create_btn_text}}</button>
    </div>
    {% include common/table/table.html %}
</div>
"""

    @xauth.login_required()
    def handle_page(self):
        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head("ID", "category_id")
        table.add_head("名称", "name", css_class_field="type_class")
        table.add_head("描述", "description")
        table.add_head("标签数量", "tag_amount")
        table.add_head("修改时间", "mtime")
        table.add_head("排序", "sort_order")

        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm, msg_field="delete_msg", css_class="btn danger")

        user_id = xauth.current_user_id()
        category_list = TagCategoryService.list(user_id=user_id)
        for row in category_list:
            row["edit_url"] = f"?action=edit&category_id={row.category_id}"
            row["delete_url"] = f"?action=delete&category_id={row.category_id}"
            row["delete_msg"] = "确认删除记录吗?"
            table.add_row(row)

        kw = Storage()
        kw.create_btn_text = "新建类别"
        kw.table = table
        kw.page = 1
        kw.page_max = 1
        kw.page_url = "?page="
        return self.response_page(**kw)
    
    def handle_edit(self):
        category_id = xutils.get_argument_int("category_id")
        category_info = TagCategoryService.get_by_id(category_id)
        if category_info is None:
            category_info = TagCategoryDO()

        user_id = xauth.current_user_id()
        form = self.create_form()
        form.add_row(field="category_id", value=str(category_id), css_class="hide")
        form.add_row(field="user_id", value=str(user_id), css_class="hide")
        form.add_row(title="名称", field="name", value=category_info.name)
        form.add_row(title="描述", field="description", value=category_info.description, type=FormRowType.textarea)
        form.add_row(title="排序", field="sort_order", value=str(category_info.sort_order))

        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def handle_save(self):
        param = self.get_data_dict()
        category_id = param.get_int("category_id")
        name = param.get_str("name")
        description = param.get_str("description")
        sort_order = param.get_int("sort_order")
        user_id = xauth.current_user_id()

        if category_id > 0:
            category_info = TagCategoryService.get_by_id(category_id)
            if category_info is None:
                return webutil.FailedResult(code="404", message="记录不存在")
        else:
            category_info = TagCategoryDO()
            category_info.user_id = user_id
        
        category_info.name = name
        category_info.description = description
        category_info.sort_order = sort_order
        TagCategoryService.save(category_info)
        return webutil.SuccessResult()


class TagManageHandler(BaseTagManageHandler):

    PAGE_HTML = """
{% include note/page/taglist_tab.html %}
{% include note/page/taglist_subtab.html %}

<div class="card">
    {% include common/table/table.html %}
    <div class="pad-top-5 pad-bottom-5">
        {% include common/base/pagination.html %}
    </div>
</div>
"""


    @xauth.login_required()
    def handle_page(self):
        page = xutils.get_argument_int("page", 1)
        tag_type = xutils.get_argument_int("tag_type")
        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head("ID", "tag_id")
        table.add_head("标签类别", "category_name")
        table.add_head("对象类型", "tag_type")
        table.add_head("名称", "tag_code", css_class_field="type_class")
        table.add_head("标签数量", "amount")
        table.add_head("修改时间", "mtime")

        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm, msg_field="delete_msg", css_class="btn danger")
        user_id = xauth.current_user_id()
        page_size = 20
        offset = (page-1) * page_size

        category_dict = TagCategoryService.get_name_dict(user_id=user_id)
        rows, count = TagInfoService.get_page(user_id=user_id, offset=offset, tag_type=tag_type, limit=page_size)
        for row in rows:
            row["edit_url"] = f"?action=edit&tag_id={row.tag_id}"
            row["category_name"] = category_dict.get(row.category_id, "")
            table.add_row(row)

        kw = Storage()
        kw.table = table
        kw.page = page
        kw.page_total = count
        kw.page_url = f"?tag_type={tag_type}&page="
        kw.show_tag_type = True
        kw.tag_type_list = TagTypeEnum.enums()
        kw.default_tab = "manage"
        kw.default_subtab = "tag"

        return self.response_page(**kw)
    
    def handle_edit(self):
        user_id = xauth.current_user_id()
        tag_id = xutils.get_argument_int("tag_id")
        tag_info = TagInfoService.get_by_id(tag_id, user_id=user_id)
        if tag_info is None:
            return webutil.FailedResult(message="标签不存在")

        
        form = self.create_form()
        form.path = "/note/tag_manage"
        form.add_row(title="标签ID", field="tag_id", value=str(tag_id), readonly=True)
        form.add_row(title="名称", field="name", value=tag_info.tag_code, readonly=True)
        row = form.add_row(title="标签类别", field="category_id", value=str(tag_info.category_id), type=FormRowType.select)
        row.add_option(title="[未设置]", value="0")
        for category in TagCategoryService.list(user_id=user_id):
            row.add_option(title=category.name, value=str(category.category_id))

        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def handle_save(self):
        user_id = xauth.current_user_id()
        params = self.get_data_dict()

        tag_id = params.get_int("tag_id")
        tag_info = TagInfoService.get_by_id(tag_id, user_id=user_id)
        if tag_info is None:
            return webutil.FailedResult(message="标签不存在")
        
        tag_info.category_id = params.get_int("category_id")
        TagInfoService.update(tag_info)
        return webutil.SuccessResult()

xurls = (
    r"/note/tag_manage", TagManageHandler,
    r"/note/tag_category_manage", TagCategoryManageHandler,
)