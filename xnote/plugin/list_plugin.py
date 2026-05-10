import xutils
from xnote.core.xtemplate import BasePlugin
from xnote.plugin.utils import ParamDict
from xutils import jsonutil
from xutils import webutil
from xutils import Storage
from xnote.webui import ListView, ListViewItem
from xnote.plugin import DataForm, FormRowType, FormRowDateType
from .base import BasePluginV2

class BaseListPlugin(BasePluginV2):
    rows = 0

    page_html = """
{% include common/script/load_select2.html %}
{% include common/script/load_laydate.html %}

<div class="card">
    {% render list_view %}
</div>

{% init page_max = 0 %}
{% init page_total = 0 %}
{% if page_max > 0 or page_total > 0 %}
    <div class="card">
        {% include common/pagination.html %}
    </div>
{% end %}
"""

    edit_html = """
<div class="card">
    {% include common/form/form.html %}
</div>
"""
    
    def get_page_html(self):
        """可以通过重写这个方法实现自定义的动态页面"""
        return self.page_html

    def response_page(self, **kw):
        page_html = self.get_page_html()
        self.writehtml(page_html, **kw)
        
    def response_form(self, **kw):
        return self.response_ajax(self.edit_html, **kw)

    def handle(self, input=""):
        action = xutils.get_argument_str("action")
        method = getattr(self, "handle_" + action, None)
        if method != None:
            return method()
        return self.handle_page()

    def handle_edit(self):
        form = self.create_form()
        form.add_heading("基础信息")

        form.add_row("id", "id", css_class="hide")
        form.add_row("只读属性", "readonly_attr", value="test", readonly=True)
        
        row = form.add_row("类型", "type", type=FormRowType.select)
        row.add_option("类型1", "1")
        row.add_option("类型2", "2")
        
        form.add_row("标题", "title")
        form.add_row("日期", "date", type=FormRowType.date)
        form.add_row("内容", "content", type=FormRowType.textarea)

        form.add_heading("高级信息")
        form.add_row("备注信息")
        
        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def get_param_dict(self) -> ParamDict:
        data = xutils.get_argument_str("data")
        data_dict = jsonutil.fromjson(data)
        return ParamDict(data_dict)
    
    get_data_dict = get_param_dict
    
    def handle_save(self):
        # data_dict = self.get_data_dict()
        return webutil.FailedResult(code="500", message="Not Implemented")
    
    def handle_page(self):
        list_view = self.create_list_view()

        for i in range(1, 6):
            list_view.add_item(ListViewItem(
                text=f"row{i}", badge_info="test", 
                icon_class="fa fa-file-text-o",
                show_chevron_right=True))

        kw = Storage()
        kw.list_view = list_view
        kw.page = 1
        kw.page_max = 1
        kw.page_url = "?page="

        return self.response_page(**kw)

    def handle_delete(self):
        # data_id = xutils.get_argument_int("data_id")
        return webutil.FailedResult(code="500", message="Not Implemented")
    
    def create_list_view(self):
        return ListView()

    def create_form(self):
        return DataForm()
