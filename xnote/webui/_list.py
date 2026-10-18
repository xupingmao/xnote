import typing

from .base import BaseContainer, Div
from xnote.core import xtemplate
from .component import ConfirmButton, ActionButton, TextTag, escape_html, TextSpan, TextLink, TextBr, RawHtml, TextNbsp, TextItemSep
from xnote.core import xconfig
from .container import TextContainer, ActionBar
from ._switch import Switch
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
<div class="list-item no-padding list-item-outer"{% for k, v in item.extra_attrs.items() %} {{k}}="{{v}}"{% end %}>
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
<div class="list-item {{item.css_class}}"{% for k, v in item.extra_attrs.items() %} {{k}}="{{v}}"{% end %}>
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
            css_class="", extra_attrs: typing.Optional[typing.Dict[str, str]] = None) -> None:
        super().__init__()
        self.text = text
        self.css_class = css_class
        self.icon_class = icon_class
        self.href = xconfig.WebConfig.resolve_path(href)
        self.badge_info = badge_info
        self.show_chevron_right = show_chevron_right
        self.tags = []
        self.action_html = action_html
        # 容器上的额外 HTML 属性（如 tag-select 行需要的 data-multiple/data-type 等）
        self.extra_attrs = extra_attrs or {}
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

class ListViewDropdown(ListViewItem):
    """ListView 内的下拉选择行。

    复用 ListViewItem 的 .list-item 外壳与 .float-right 布局，
    仅在右侧 extra 区渲染一个 <select>。
    """

    _select_code = xtemplate.compile_template("""
<select name="{{item.name}}" data-type="{{item.data_type}}" value="{{item.value}}" class="{{item.select_css_class}}">
    {% for option in item.options %}
        <option value="{{option.value}}">{{option.name}}</option>
    {% end %}
</select>
""")

    def __init__(self, text="", name="", data_type="int", value="", select_css_class=""):
        super().__init__(text=text)
        self.name = name
        self.data_type = data_type
        self.value = value
        self.select_css_class = select_css_class
        self.options = []

    def add_option(self, name="", value=""):
        self.options.append(_ListViewOption(name=name, value=value))
        return self

    def render(self):
        # 把 <select> 放进右侧 float-right 的 extra 区，复用父类的 .list-item 外壳
        select_html = self._select_code.generate(item=self)
        self.extra.children = [RawHtml(select_html)]
        return super().render()


class ListViewTagSelect(ListViewItem):
    """ListView 内的 tag 选择器行。

    复用 ListViewItem 的 .list-item 外壳与 .float-right 布局；
    容器属性（data-multiple / data-type / data-p / data-readonly）写到 extra_attrs，
    由 x-tag-select.js 读取；选项渲染为右侧 float-right 的 .tag 点选。
    """

    def __init__(self, text="", name="", value="", multiple=False, readonly=False,
                 css_class="list-item list-tag-select tag-select", data_type="", data_p=""):
        super().__init__(text="", css_class=css_class)
        self.name = name
        self.value = value
        self.multiple = multiple
        self.readonly = readonly
        self.data_type = data_type
        self.data_p = data_p
        # 容器属性（x-tag-select.js 读取），直接挂到 .list-item 外壳上
        self.extra_attrs["data-multiple"] = "true" if multiple else "false"
        if readonly:
            self.extra_attrs["data-readonly"] = "1"
        if data_type:
            self.extra_attrs["data-type"] = data_type
        if data_p:
            self.extra_attrs["data-p"] = data_p
        if text:
            self.add_span(text=text, css_class="tag-select-label")
        # 隐藏域（值的唯一来源），位于内容区（非 float-right）
        self.add(RawHtml('<input type="hidden" name="%s" class="form-row-value" value="%s">'
                         % (escape_html(self.name), escape_html(self.value_str))))

    @property
    def value_str(self) -> str:
        """规整为逗号分隔字符串，用于隐藏域（兼容 list / 逗号串 / 空值）"""
        value = self.value
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ",".join(str(v) for v in value)
        return str(value)

    @property
    def selected_values(self) -> typing.List[str]:
        value_str = self.value_str
        if not value_str:
            return []
        return [v for v in value_str.split(",") if v != ""]

    def add_option(self, title="", value=""):
        """添加选项（渲染为右侧 .tag 点选）"""
        cls = "tag lightblue"
        if value in self.selected_values:
            cls += " active"
        self.extra.add(RawHtml('<span class="%s" data-value="%s">%s</span>'
                               % (cls, escape_html(value), escape_html(title))))
        return self

    # render 继承自 ListViewItem


class ListViewSwitch(ListViewItem):
    """ListView 内的开关行。

    复用 ListViewItem 的 .list-item 外壳与 .float-right 布局；
    开关组件（Switch）放在右侧 extra 区，值变化时经 oninput_ajax_url 回调后端。
    """

    def __init__(self, text="", name="", checked: bool = False,
                 on_value="1", off_value="0", oninput_ajax_url="", css_class=""):
        super().__init__(text=text, css_class=css_class)
        self.switch = Switch(name=name, text="", checked=checked,
                             on_value=on_value, off_value=off_value,
                             oninput_ajax_url=oninput_ajax_url)
        self.extra.add(self.switch)

    @property
    def name(self) -> str:
        return self.switch.name

    @property
    def value(self) -> str:
        return self.switch.hidden_value

    # render 继承自 ListViewItem


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
            return pagination.render_str()
        return ""

    def add_item(self, item: ListViewItem):
        self.add(item)

    def render(self):
        return self._code.generate(item_list = self.children, action_bar = self.action_bar,
                                   pagination_html = self.render_pagination_html())
    
    def add_dropdown(self, text="", name="", data_type="int", value="", select_css_class=""):
        dropdown = ListViewDropdown(text=text, name=name, data_type=data_type,
                                   value=value, select_css_class=select_css_class)
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

    def add_switch(self, text="", name="", value="", on_value="1", off_value="0",
                   oninput_ajax_url="", css_class=""):
        """添加开关行（列表行外壳 + 右对齐开关）。

        开关值变化时通过 oninput_ajax_url 回调后端（与 FormRow.oninput_ajax_url 一致）：
        前端 x-switch.js 在切换后对该隐藏域发起 requestOnInputAjax 请求，
        后端返回 xnote.executeCommands 可执行的命令列表（如 reload / update_text）。
        oninput_ajax_url 应包含 key/type/p 等查询参数，例如
        f"/system/config?key={name}&type=int&p=sys"。

        value 是字符串（"1"/"0"/"true" 等），而开关 checked 需要 bool，这里统一解析。
        """
        checked = Switch.parse_checked(value)
        switch_row = ListViewSwitch(text=text, name=name, checked=checked,
                                    on_value=on_value, off_value=off_value,
                                    oninput_ajax_url=oninput_ajax_url, css_class=css_class)
        self.add(switch_row)
        return switch_row

ItemList = ListView
ListItem = ListViewItem
