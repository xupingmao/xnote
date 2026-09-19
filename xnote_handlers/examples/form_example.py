# encoding=utf-8
# Form 示例 tab，对应 /examples/example/form
# Form 组件示例：静态展示表单 / 查询表单 / 弹窗表单
import xutils

from xutils import Storage
from xutils import webutil
from xnote.plugin.table_plugin import BaseTablePlugin, BasePlugin
from xnote.plugin import DataTable, TableActionType, TabBox, QueryForm, TabTable, DataForm, PageEditForm, DialogForm, EditFormButton
from xnote.webui import FormRowType
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab


class FormExampleHandler(BaseTablePlugin):
    """Form 组件示例：静态展示表单 / 查询表单 / 弹窗表单"""

    parent_link = LinkConfig.develop_index

    body_html = """
{% include examples/component/example_nav_tab.html %}

<h3 class="card-title">页面表单 (PageEditForm 渲染，普通文档流，非弹窗)</h3>
<div class="card">
    {% render static_form %}
</div>

<h3 class="card-title">查询表单 (QueryForm 渲染)</h3>
<div class="card">
    {% render query_form %}
</div>

<h3 class="card-title">弹窗表单 (DialogForm 定义表单，EditFormButton 触发)</h3>
<div class="card">
    {% render dialog_form %}
</div>
"""

    def handle(self, input=""):
        action = xutils.get_argument_str("action")
        if action == "edit":
            return self.handle_edit()
        if action == "save":
            return self.handle_save()
        return self.handle_page()

    def handle_page(self):
        # 页面表单：PageEditForm（page_edit 类型），渲染为普通文档流的页面表单，
        # 区别于弹窗用的 edit 类型（DataForm，absolute 定位，仅适合对话框容器）
        static_form = PageEditForm()
        static_form.add_heading("基础信息")
        static_form.add_row("名称", "name", value="示例名称")
        type_row = static_form.add_select("类型", "type", value="1")
        type_row.add_option("类型1", "1")
        type_row.add_option("类型2", "2")
        static_form.add_date_input("日期", "date", value="2020-01-01")
        static_form.add_row("内容", "content", type=FormRowType.textarea, value="示例内容")
        static_form.add_image("封面图片", "cover", value="/_static/xnote.png")

        # 查询表单
        query_form = QueryForm()
        query_form.add_row("标题", "title")
        q_type_row = query_form.add_select("类型", "type")
        q_type_row.add_option("全部", "")
        q_type_row.add_option("类型1", "1")
        q_type_row.add_option("类型2", "2")
        query_form.add_date_input("日期", "date")

        # 弹窗表单触发按钮（单独的组件，不塞进表单里）
        dialog_form = EditFormButton(text="打开弹窗表单",
                                     url="/examples/example/form?action=edit")

        kw = Storage()
        kw.static_form = static_form
        kw.query_form = query_form
        kw.dialog_form = dialog_form
        kw.example_tab = get_example_tab(tab_default="form")
        self.writehtml(self.body_html, **kw)

    def handle_edit(self):
        # DialogForm 是 DataForm 的语义化别名，专用于弹窗场景
        form = DialogForm()
        form.add_heading("基础信息")
        form.add_row("名称", "name", value="弹窗表单示例")
        row = form.add_select("类型", "type", value="1")
        row.add_option("类型1", "1")
        row.add_option("类型2", "2")
        form.add_date_input("日期", "date")
        form.add_row("内容", "content", type=FormRowType.textarea)

        kw = Storage()
        kw.form = form
        return self.response_form(**kw)

    def handle_save(self):
        return webutil.SuccessResult()


xurls = (
    r"/examples/example/form", FormExampleHandler,
)
