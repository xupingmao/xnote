import typing

from .base import BaseComponent, BaseContainer, Div
from xnote.core import xtemplate
from .component import ConfirmButton, ActionButton, TextTag, escape_html, TextSpan, TextLink, TextBr, RawHtml, TextNbsp, TextItemSep
from xnote.core import xconfig
from .container import TextContainer, ActionBar
from ._tag_select import TagSelect
from ._pagination import Pagination


class ListViewLine(TextContainer):
    """列表项内的一个子行（line），可承载标签、辅助文本等组件。
    渲染为 <div class="list-item-line">...</div>；一个 ListViewItem 可包含多行。"""
    def __init__(self, css_class="", css_style=""):
        super().__init__(css_class="list-item-line " + css_class, css_style=css_style)
        self.extra = TextContainer("row-extra")
        self.add(self.extra)


class ListViewItem(TextContainer):
    # 是否展示右箭头
    show_chevron_right = False
    # 操作按钮
    action_btn : typing.Optional[ActionButton] = None
    # 不推荐使用, 标签列表（渲染在链接内，向后兼容已有列表）
    tags: typing.List[TextTag]
    # 默认链接在外部
    is_link_outside = True

    _outside_html = """
<div class="list-item no-padding list-item-outer">
    <a class="list-item-link {{item.css_class}}" href="{{ item.href }}">
        {% if item.icon_class %}
            <i class="{{item.icon_class}}"></i>
        {% end %}
        {% raw item._children_html %}
        {% for tag in item.tags %} {% render tag %} {% end %}
    </a>
    {% raw item._extra_html %}
</div>
"""

    _inside_html = """
<div class="list-item {{item.css_class}}">
    {% if item.icon_class %}
        <i class="{{item.icon_class}}"></i>
    {% end %}
    {% raw item._children_html %}
    {% for tag in item.tags %} {% render tag %} {% end %}
    
    {% raw item._extra_html %}
</div>
"""

    _outside_code = xtemplate.compile_template(_outside_html)
    _intside_code = xtemplate.compile_template(_inside_html)

    def __init__(
            self, text="", href="", icon_class="", badge_info="", 
            show_chevron_right = False, action_html = "",
            css_class="") -> None:
        super().__init__()
        self.text = text
        self.css_class = css_class
        self.icon_class = icon_class
        self.href = xconfig.WebConfig.resolve_path(href)
        self.badge_info = badge_info
        self.show_chevron_right = show_chevron_right
        self.tags = []
        self.action_html = action_html
        self.extra = TextContainer(css_class="float-right list-item-extra")
        self._extra_html = ""

        if text:
            self.add_span(text=text)

        if href == "":
            self.is_link_outside = False

    @property
    def right_div(self):
        # deprecated: 请使用 extra 替代
        return self.extra

    def add_line(self, css_class="", css_style=""):
        """新增一个子行（line），返回 ListViewLine 以便继续添加内容。

        注意：icon_class 是 inline 元素，会和第一个 inline 子内容（add_span/add_link 等）
        排在同一行；如果先调 add_line()（block 元素），icon 会单独占一行。
        多行 item 的第一行请用 add_span/add_link 等 inline 内容，后续行再用 add_line()。
        """
        line = ListViewLine(css_class=css_class, css_style=css_style)
        self.add(line)
        return line

    def render(self):
        self._children_html = "".join([item.render_str() for item in self.children])
        self._extra_html = self._render_extra_html()

        if self.is_link_outside:
            return self._outside_code.generate(item = self)
        else:
            return self._intside_code.generate(item = self)

    def _render_extra_html(self):
        new_extra = Div(css_class=self.extra.css_class, css_style=self.extra.css_style)
        if self.badge_info:
            new_extra.add(TextSpan(text=self.badge_info, css_class="badge-info"))
        if self.action_btn:
            new_extra.add(self.action_btn)
        if self.action_html:
            new_extra.add(RawHtml(self.action_html))

        for child in self.extra.children:
            new_extra.add(child)

        if self.show_chevron_right:
            new_extra.add(RawHtml(' <i class="fa fa-chevron-right"></i>'))
        return new_extra.render()

class _ListViewOption:

    def __init__(self, name="", value=""):
        self.name = name
        self.value = value

class ListViewDropdown(BaseComponent):

    _code = xtemplate.compile_template("""
<div class="list-item {{item.css_class}}">

{% if item.icon_class %}
    <i class="{{item.icon_class}}"></i>
{% end %}

    <span>{{ item.text }}</span>
                                       
{% for tag in item.tags %} {% render tag %} {% end %}
<div class="float-right">
    <select name="{{item.name}}" data-type="{{item.data_type}}" value="{{item.value}}">
        {% for option in item.options %}
            <option value="{{option.value}}">{{option.name}}</option>
        {% end %}
    </select>
    {% if item.show_chevron_right %}
        <i class="fa fa-chevron-right"></i>
    {% end %}
</div>

</div>
""")
    
    show_chevron_right = False
    # 标签列表
    tags: typing.List[TextTag]

    icon_class = ""
    css_class = ""
    
    def __init__(self, text="", name="", data_type="int", value=""):
        self.text = text
        self.name = name
        self.data_type = data_type
        self.value = value
        self.tags = []
        self.options = []

    def add_option(self, name="", value=""):
        self.options.append(_ListViewOption(name=name, value=value))

    def render(self):
        return self._code.generate(item = self)


class ListViewTagSelect(BaseComponent):
    """ListView 内的 tag 选择器行（列表行外壳 + 右对齐布局由本类负责）。

    采用组合模式：内部持有一个通用 TagSelect 实例负责选项与选中值的管理，
    本类只负责列表行特有的 .list-item 外壳与 .float-right 右对齐布局，
    不再通过继承 TagSelect 与之耦合。
    """

    _code = xtemplate.compile_template("""
<div class="{{item.css_class}} tag-select" data-multiple="{{'true' if item.multiple else 'false'}}" {% if item.readonly %}data-readonly="1"{% end %}{% if item.data_type %} data-type="{{item.data_type}}"{% end %}{% if item.data_p %} data-p="{{item.data_p}}"{% end %}>

{% if item.icon_class %}
    <i class="{{item.icon_class}}"></i>
{% end %}

{% if item.text %}
    <span class="tag-select-label">{{ item.text }}</span>
{% end %}

    <input type="hidden" name="{{item.name}}" class="form-row-value" value="{{item.value}}">

<div class="float-right">
{% for option in item.options %}
    <span class="tag lightblue {% if option.value in item.selected_values %}active{% end %}" data-value="{{option.value}}">{{option.title}}</span>
{% end %}
</div>

</div>
""")

    def __init__(self, text="", name="", value="", multiple=False, readonly=False, css_class="list-item list-tag-select", data_type="", data_p=""):
        super().__init__()
        # 组合通用 TagSelect：选项与选中值的管理交给它，本类只负责列表行布局
        self.selector = TagSelect(text=text, name=name, value=value,
                                  multiple=multiple, readonly=readonly,
                                  data_type=data_type, data_p=data_p)
        self.css_class = css_class
        self.multiple = multiple
        self.readonly = readonly
        self.data_type = data_type
        self.data_p = data_p

    # 渲染所需的属性统一委托给组合的 TagSelect，保证单一数据源
    @property
    def text(self):
        return self.selector.text

    @property
    def name(self):
        return self.selector.name

    @property
    def value(self):
        return self.selector.value

    @property
    def selected_values(self):
        return self.selector.selected_values

    @property
    def icon_class(self):
        return self.selector.icon_class

    @property
    def options(self):
        return self.selector.options

    def add_option(self, title="", value=""):
        """添加选项（委托给组合的 TagSelect）"""
        self.selector.add_option(title, value)
        return self

    def render(self):
        return self._code.generate(item=self)


class ListView(BaseContainer):    
    _code = xtemplate.compile_template("""
{% render action_bar %}
{% if len(item_list) == 0 %}
    <div class="row">
    {% include common/text/empty_text.html %}
    </div>
{% end %}

{% for item in item_list %}
    {% render item %}
{% end %}

{% raw pagination_html %}
""")

    def __init__(self, css_class="", css_style="", html="", id=""):
        super().__init__(css_class=css_class, css_style=css_style, html=html, id=id)
        self.pagination: typing.Optional[Pagination] = None
        self.action_bar = ActionBar()

    def set_pagination(self, page=1, page_max=0, page_total=0, page_size=20,
                       page_url="", page_arg_name="page", **kw: typing.Any) -> Pagination:
        """设置分页信息, 设置之后列表底部会自动渲染分页组件

        Arguments:
            - page: 当前页码
            - page_max: 最大页码, 不传时由 page_total/page_size 计算
            - page_total: 总记录数
            - page_size: 每页记录数
            - page_url: 分页的基础URL, 不传时使用当前页面的URL
            - page_arg_name: 分页参数名, 默认 page(比如评论用 comment_page)
            - kw: 兼容调用方直接透传模板变量(set_pagination(**kw)), 多余的参数会被忽略
        """
        self.pagination = Pagination(page=page, page_max=page_max, page_total=page_total,
                                     page_size=page_size, page_url=page_url,
                                     page_arg_name=page_arg_name)
        return self.pagination

    def render_pagination_html(self) -> str:
        """渲染分页的HTML(模板内部使用)"""
        pagination = self.pagination
        if pagination is not None:
            div = Div(css_class="row py-2")
            div.add(pagination)
            return div.render_str()
        return ""

    def add_item(self, item: ListViewItem):
        self.add(item)

    def render(self):
        return self._code.generate(item_list = self.children, action_bar = self.action_bar,
                                   pagination_html = self.render_pagination_html())
    
    def add_dropdown(self, text="", name="", data_type="int", value=""):
        dropdown = ListViewDropdown(text=text, name=name, data_type=data_type, value=value)
        self.add(dropdown)
        return dropdown

    def add_tag_select(self, text="", name="", value="", multiple=False, readonly=False, css_class="", data_type="", data_p=""):
        """添加 tag 风格的选择器（默认单选，点选标签，提交逗号分隔值）。

        选项通过返回的 ListViewTagSelect.add_option(title, value) 添加，用法与 DataForm.add_tag_select 一致。
        多选传 multiple=True，提交值为逗号分隔的多个值。
        data_type / data_p 透传到容器，供配置提交逻辑读取（如 settings 页的 updateSetting）。
        """
        tag_select = ListViewTagSelect(text=text, name=name, value=value,
                                       multiple=multiple, readonly=readonly,
                                       data_type=data_type, data_p=data_p)
        if css_class:
            tag_select.css_class = css_class
        self.add(tag_select)
        return tag_select

ItemList = ListView
ListItem = ListViewItem
