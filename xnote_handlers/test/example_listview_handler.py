import xutils
import copy

from xutils import webutil, Storage
from xutils import dateutil
from xnote.plugin.list_plugin import BaseListPlugin, BasePlugin
from xnote.webui import ListView, ListViewItem, ListItem, TextTag
from xnote.plugin.component import ConfirmButton, BaseContainer, ActionButton
from xnote.plugin import TabBox
from xnote_handlers.config import LinkConfig
from .example_handler import get_example_tab
from xnote.webui import TextLink, EditFormActionLink, ConfirmActionLink
from xnote.webui import FormRowType

class ListPluginHandler(BaseListPlugin):
    title = "ListPlugin示例"
    parent_link = LinkConfig.develop_index

    tab_html = """
<div class="card">
    {% render example_tab %}
</div>

<div class="card">
    {% render tab1 %}
    {% render tab2 %}
</div>
"""

    def handle_page(self):
        title_width = "60px"
        tab1 = TabBox(tab_key="list_key", css_class="btn-style", title="筛选1", tab_default="all")
        tab1.add_item(title="全部", value="all")
        tab1.add_item(title="选项1", value="option1")
        tab1.add_item(title="选项2", value="option2")
        tab1.title_width = title_width

        tab2 = TabBox(tab_key="tab2", css_class="btn-style", title="筛选2", tab_default="all")
        tab2.add_item(title="全部", value="all")
        tab2.add_item(title="选项A", value="op1")
        tab2.add_item(title="选项B", value="op2")
        tab2.title_width = title_width
    
        list_view = self.create_list_view()
        now = dateutil.format_date()
        
        for i in range(1, 6):
            text = f"标题 - row{i}"
            list_item = ListViewItem(
                badge_info="角标信息",
                icon_class="fa fa-file-text-o",
                show_chevron_right=True)
            list_item.add_span(text=text, css_class="bold")
            list_item.add_br()
            list_item.add_span("说明XXX", css_class="gray")
            list_item.add_link(text=" 详情", href="")
            list_item.add_br()
            
            # 新行的第一个分隔符会自动跳过
            list_item.add_item_sep()
            list_item.add_span(f"更新于 {now}", css_style="color:#999;")
            list_item.add_item_sep()
            list_item.add_span("标签", css_class="gray")
            
            quote_text = xutils.quote(text)
            list_item.extra.add(EditFormActionLink(text="编辑", url=f"?action=edit&value={quote_text}"))
            list_item.extra.add(ConfirmActionLink(text="删除", url="?action=delete", msg=f"确认删除[{text}]吗?", css_class="danger"))
            
            list_view.add_item(list_item)

        kw = Storage()
        kw.list_view = list_view
        kw.page_current = 1
        kw.page_total = 100
        kw.page_url = "?page="

        self.writehtml(
            self.tab_html, 
            tab1 = tab1,
            tab2 = tab2,
            example_tab = get_example_tab(tab_default="list_plugin"))
        return self.response_page(**kw)
    
    def handle_edit(self):
        value = xutils.get_argument_str("value")
        form = self.create_form()
        form.add_row("id", "id", css_class="hide")
        form.add_row("只读属性", "readonly_attr", value="test", readonly=True)
        
        row = form.add_select("类型", "type")
        row.add_option("类型1", "1")
        row.add_option("类型2", "2")

        form.add_date_input("日期", "date")
        form.add_row("内容", "content", type=FormRowType.textarea, value=value)

        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    


class ListExampleHandler(BasePlugin):
    parent_link = LinkConfig.develop_index
    title = "ListView示例"
    rows = 0
    body_html = """
{% include test/component/example_nav_tab.html %}

<div class="card">
    <span class="card-title">ListView: 外层链接</span>
    {% render item_list %}
</div>

<div class="card">
    <span class="card-title">ListView: 内层链接</span>
    {% render item_list2 %}
</div>
"""
    def handle(self, input=""):
        item_list = ListView()
        item_list2 = ListView()

        action = xutils.get_argument_str("action")
        if action == "delete":
            return self.handle_delete()

        for index in range(5):
            text = f"物品-{index+1}"
            item = ListItem(text=text, href=f"javascript:xnote.alert({index+1})", badge_info=f"徽标{index+1}")
            item.show_chevron_right = True
            if index % 2 == 0:
                item.icon_class = "fa fa-file-text-o"
            else:
                item.icon_class = "fa fa-list"
                item.tags.append(TextTag(text="标签", css_class="lightblue"))
                item.tags.append(TextTag(text="标签2", css_class="orange"))
            item.action_btn = ConfirmButton(text="删除", url="?action=delete", message=f"确认删除[{text}]吗", css_class="btn danger")
            
            item_list.add_item(item)

            item2 = copy.deepcopy(item)
            item2.is_link_outside = False
            item2.show_chevron_right = False
            item_list2.add_item(item2)

        kw = Storage()
        kw.item_list = item_list
        kw.item_list2 = item_list2
        kw.example_tab = get_example_tab()

        self.writehtml(html=self.body_html, **kw)

    def handle_delete(self):
        return webutil.FailedResult(code="500", message="mock删除失败")

xurls = (
    r"/test/example/list", ListExampleHandler,
    r"/test/example/list_plugin", ListPluginHandler,
)