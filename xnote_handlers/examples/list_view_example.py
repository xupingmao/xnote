import xutils
import copy

from xutils import webutil, Storage
from xutils import dateutil
from xnote.plugin.list_plugin import BaseListPlugin, BasePlugin
from xnote.webui import ListView, ListViewItem, ListItem, TextTag
from xnote.webui import ConfirmButton, BaseContainer, ActionButton
from xnote.plugin import TabBox
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab
from xnote.webui import TextLink, EditFormActionLink, ConfirmActionLink
from xnote.webui import FormRowType
from xnote.webui import ActionBar

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
        list_view.action_bar.add_span("操作栏")
        list_view.action_bar.add_edit_button("操作1")
        list_view.action_bar.add_edit_button("操作2")
        
        action_bar2 = ActionBar()
        action_bar2.add_span("操作栏2")
        action_bar2.extra.add_edit_button("操作1")
        action_bar2.extra.add_confirm_button("操作2")
        
        list_view.add(action_bar2)
        
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
            list_item.extra.add(ConfirmActionLink(text="删除", url="?action=delete", msg=f"确认删除[{text}]吗?", css_class="red"))
            
            list_view.add_item(list_item)
            
        page = xutils.get_argument_int("page", 1)

        # 分页直接设置到列表组件上, 列表底部会自动渲染分页
        list_view.set_pagination(page=page, page_total=100, page_size=20)

        kw = Storage()
        kw.list_view = list_view

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
    


class ListViewExampleHandler(BasePlugin):
    parent_link = LinkConfig.develop_index
    title = "ListView示例"
    rows = 0
    body_html = """
{% include examples/component/example_nav_tab.html %}

<div class="card">
    <span class="card-title">ListView: 外层链接</span>
    {% render item_list %}
</div>

<div class="card">
    <span class="card-title">ListView: 内层链接</span>
    {% render item_list2 %}
</div>

<div class="card">
    <span class="card-title">ListView: 2行item（标题 + 说明）</span>
    {% render item_list_two_line %}
</div>

<div class="card">
    <span class="card-title">ListView: 3行item（标题 + 说明 + 元信息）</span>
    {% render item_list_three_line %}
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
        kw.item_list_two_line = self.create_two_line_list()
        kw.item_list_three_line = self.create_three_line_list()
        kw.example_tab = get_example_tab(tab_default="list_view")

        self.writehtml(html=self.body_html, **kw)

    def create_two_line_list(self):
        """2行item：第一行是标题（加粗 + 标签），第二行是灰色说明文字。
        注意：icon 是 inline 元素，第一行要用 add_span 等 inline 内容与 icon 同行，
        不能先 add_line()（block），否则 icon 会单独占一行。"""
        list_view = ListView()

        for index in range(2):
            item = ListItem(icon_class="fa fa-file-text-o", show_chevron_right=True,
                            href=f"javascript:xnote.alert({index+1})")

            # 第一行：icon + 标题 + 标签（inline 内容，与 icon 同行）
            item.add_span(text=f"物品-{index+1}", css_class="bold")
            item.add(TextTag(text="标签", css_class="lightblue"))

            # 第二行：说明
            desc_line = item.add_line()
            desc_line.add_span(text="说明：这里是第二行内容", css_class="gray")

            list_view.add_item(item)

        return list_view

    def create_three_line_list(self):
        """3行item：标题 + 说明 + 元信息行（更新时间 | 来源）。
        同 create_two_line_list：第一行用 inline 内容与 icon 同行，后续行用 add_line()。"""
        list_view = ListView()
        now = dateutil.format_date()

        for index in range(2):
            item = ListItem(icon_class="fa fa-list", show_chevron_right=True,
                            badge_info=f"徽标{index+1}",
                            href=f"javascript:xnote.alert({index+1})")

            # 第一行：icon + 标题
            item.add_span(text=f"物品-{index+1}", css_class="bold")

            # 第二行：说明
            desc_line = item.add_line()
            desc_line.add_span(text="说明：这里是第二行内容", css_class="gray")

            # 第三行：元信息（行内可用 add_icon 加图标）
            meta_line = item.add_line()
            meta_line.add_icon("fa fa-clock-o")
            meta_line.add_nbsp()
            meta_line.add_span(text=f"更新于 {now}", css_style="color:#999;")
            meta_line.add_item_sep()
            meta_line.add_span(text="来源：示例", css_style="color:#999;")

            list_view.add_item(item)

        return list_view

    def handle_delete(self):
        return webutil.FailedResult(code="500", message="mock删除失败")

xurls = (
    r"/examples/list_view", ListViewExampleHandler,
    r"/examples/list_plugin", ListPluginHandler,
)