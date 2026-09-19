# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 16:20:05
@LastEditors  : xupingmao
@LastEditTime : 2024-03-31 14:17:08
@FilePath     : /xnote/xnote/plugin/form.py
@Description  : 描述
"""

import typing
import itertools
from xutils import Storage
from xnote.core import xtemplate
from xnote.webui.base import BaseComponent
from xnote.webui._tag_select import TagSelect

FormValueType = typing.Union[int, str, list]

class FormType:
    # 弹窗编辑
    edit = "edit"
    # 页面编辑
    page_edit = "page_edit"
    # 查询表单
    query = "query"

class FormRowType:
    """表单行的类型"""
    input = "input"
    select = "select"
    tag_select = "tag_select"  # tag 风格的选择器（点选标签）
    textarea = "textarea"
    date = "date"
    heading = "heading"
    html = "html"
    image = "image"   # 图片上传
    file = "file"     # 文件上传

class FormRowOption:
    """表单行的选项"""
    def __init__(self):
        self.title = ""
        self.value = ""
        self.selected = False

class FormRowOptGroup:
    def __init__(self):
        self.label = ""
        self.options = []
    
    def add_option(self, title = "", value = ""):
        option = FormRowOption()
        option.title = title
        option.value = value
        self.options.append(option)

class FormRowDateType:
    """日期的类型"""
    year = "year"
    month = "month"
    date = "date"
    time = "time"
    datetime = "datetime"
    default = date

class FormRow(BaseComponent):

    date_type = FormRowDateType.date # 用于日期组件
    readonly = False
    multiple = False
    html : typing.Union[str, bytes] = ""
    rows = 0 # textarea 行数
    accept = "" # 文件选择器的 accept 属性（图片/文件上传用）
    value_list = [] # type: typing.List[Storage]  # 图片/文件上传的已有值列表，元素为 {webpath, name}

    # 远程搜索（select2 ajax）。设置 ajax_url 后由通用的 xnote.initSelect2 初始化为 ajax 选择器，
    # 兼容弹窗（html 注入、<script> 不执行）与独立页面两种场景。
    ajax_url = ""
    ajax_data = "" # 额外的查询参数(JSON字符串)，如 '{"type":"public"}'


    _select_html = """
<select id="{{row.id}}" name="{{row.field}}" class="form-row-value" value="{{row.value}}" {% raw row.html_attr %}>
    {% for opt_group in row.opt_groups %}
        <optgroup label="{{opt_group.label}}">
            {% for option in opt_group.options %}
                <option value="{{option.value}}">{{option.title}}</option>
            {% end %}
        </optgroup>
    {% end %}
    {% for option in row.options %}
        <option value="{{option.value}}"{% if option.selected %} selected{% end %}>{{option.title}}</option>
    {% end %}
</select>
"""
    _select_template = xtemplate.compile_template(_select_html, name="plugin.form.row.select")

    """数据行"""
    def __init__(self):
        self.id = ""
        self.title = ""
        self.field = ""
        self.placeholder = ""
        self.value = ""
        self.type = FormRowType.input
        self.css_class = ""
        self.options = []
        self.opt_groups = []
        self.accept = ""
        self.value_list = []

    def add_option(self, title="", value="", selected=False):
        option = FormRowOption()
        option.title = title
        option.value = value
        option.selected = selected
        self.options.append(option)
        return self
    
    def add_opt_group(self, label = ""):
        opt_group = FormRowOptGroup()
        opt_group.label = label
        self.opt_groups.append(opt_group)
        return opt_group
    
    @property
    def html_attr(self):
        result = ""
        if self.readonly:
            result += " readonly"
        
        if self.multiple:
            result += f" multiple=\"multiple\""
        
        if self.rows > 0:
            result += f" rows=\"{self.rows}\""
        
        if self.ajax_url:
            result += f' data-select2-ajax-url="{self.ajax_url}"'
            if self.ajax_data:
                result += f" data-select2-ajax-data='{self.ajax_data}'"
        
        return result
    
    def render(self):
        if self.type == FormRowType.select:
            return self.render_select()
        
        if self.type == FormRowType.tag_select:
            return self.render_tag_select()
        
        return ""
            
    def render_select(self):
        return self._select_template.generate(row = self)

    def render_tag_select(self):
        """渲染 tag 风格选择器，复用通用 TagSelect 组件。

        容器保留 .form-tag-select 类，兼容原表单的样式与 x-tag-select.js 交互。
        """
        tag_select = TagSelect(
            name=self.field,
            value=self.value,
            multiple=self.multiple,
            readonly=self.readonly,
            css_class=(self.css_class + " form-tag-select") if self.css_class else "form-tag-select",
        )
        for option in self.options:
            tag_select.add_option(option.title, option.value)
        return tag_select.render()

    
class DataForm(BaseComponent):
    """数据表格"""

    form_type = FormType.edit
    form_type_css = ""
    form_method = "POST"
    footer_btn_group_css = "float-right"
    footer_html:typing.Union[str, bytes] = ""
    save_action = "save"
    delete_confirm_msg = "Delete?"
    delete_url = ""
    delete_reload_href = ""
    delete_btn_css = ""
    # 表单id的自增序列，保证同一进程内每个表单实例的id唯一
    # （同一个页面可能存在多个表单，id重复会导致 $("#id") 定位到错误的表单）
    _id_seq = itertools.count(1)
    
    def __init__(self):
        self.id = str(next(DataForm._id_seq))
        self.row_id = 0
        self.rows = [] # type: list[FormRow]
        self.save_btn_css = ""
        self.close_btn_css = ""
        self.model_name = "default"
        self.path = ""
        self.headings = []

    def _create_row_id(self):
        self.row_id += 1
        return f"row_{self.id}_{self.row_id}"

    def add_row(self, title="", field="", placeholder="", value="", 
                type=FormRowType.input, css_class="", readonly=False,
                date_type = FormRowDateType.date):
        row = FormRow()
        row.id = self._create_row_id()
        row.title = title
        row.field = field
        row.placeholder = placeholder
        row.value = value
        row.type = type
        row.css_class = css_class
        row.readonly = readonly
        row.date_type = date_type
        
        self.rows.append(row)
        return row
    
    def _format_value(self, value: FormValueType) -> str:
        if isinstance(value, list):
            values = []
            for item in value:
                values.append(str(item))
            return ",".join(values)
        return str(value)
    
    def add_date_input(self, title = "", field = "", value = "", css_class = "", date_type = FormRowDateType.date):
        row = FormRow()
        row.id = self._create_row_id()
        row.title = title
        row.field = field
        row.value = value
        row.type = FormRowType.date
        row.css_class = css_class
        row.date_type = date_type
        
        self.rows.append(row)
        return row
    
    def add_select(self, title = "", field = "", placeholder = "", value: FormValueType = "", 
                   css_class = "", readonly = False, multiple = False):
        row = FormRow()
        row.id = self._create_row_id()
        row.type = FormRowType.select
        row.title = title
        row.field = field
        row.placeholder = placeholder
        row.value = self._format_value(value)
        row.css_class = css_class
        row.readonly = readonly
        row.multiple = multiple
        
        self.rows.append(row)
        return row
    
    def add_tag_select(self, title = "", field = "", placeholder = "", value: FormValueType = "",
                       css_class = "", readonly = False, multiple = False):
        """添加 tag 风格的选择器（默认单选，点选标签，提交逗号分隔值）

        选项通过 row.add_option(title, value) 添加，用法与 add_select 一致。
        多选时传 multiple=True，提交值为逗号分隔的多个值。
        """
        row = FormRow()
        row.id = self._create_row_id()
        row.type = FormRowType.tag_select
        row.title = title
        row.field = field
        row.placeholder = placeholder
        row.value = self._format_value(value)
        row.css_class = css_class
        row.readonly = readonly
        row.multiple = multiple
        
        self.rows.append(row)
        return row
    
    def add_textarea(self, title="", field="", placeholder="", value="", 
                css_class="", readonly=False, rows = 0):
        row = FormRow()
        row.id = self._create_row_id()
        row.title = title
        row.field = field
        row.placeholder = placeholder
        row.value = value
        row.type = FormRowType.textarea
        row.css_class = css_class
        row.readonly = readonly
        row.rows = rows
        self.rows.append(row)
        return row

    def add_heading(self, name=""):
        """添加子标题"""
        row = FormRow()
        row.id = self._create_row_id()
        row.title = name
        row.css_class = "form-heading"
        row.type = FormRowType.heading
        self.rows.append(row)

    def add_html(self, html : typing.Union[str, bytes] = ""):
        row = FormRow()
        row.id = self._create_row_id()
        row.html = html
        row.type = FormRowType.html
        self.rows.append(row)

    def add_image(self, title="", field="", value="", css_class="", multiple=True):
        """添加图片上传行（交互参考评论/随手记的图片上传）"""
        return self._add_upload_row(FormRowType.image, title, field, value, css_class, multiple, accept="image/*")

    def add_file(self, title="", field="", value="", css_class="", multiple=True):
        """添加文件上传行（交互参考评论/随手记的附件上传）"""
        return self._add_upload_row(FormRowType.file, title, field, value, css_class, multiple, accept="")

    def _normalize_upload_value(self, value):
        # type: (typing.Union[int, str, list, None]) -> list
        """把 value（逗号分隔字符串或列表）归一化为值列表"""
        if value is None:
            return []
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]

    def _add_upload_row(self, row_type, title, field, value, css_class, multiple, accept):
        row = FormRow()
        row.id = self._create_row_id()
        row.type = row_type
        row.title = title
        row.field = field
        row.css_class = css_class
        row.multiple = multiple
        row.accept = accept

        webpaths = self._normalize_upload_value(value)
        items = []
        for webpath in webpaths:
            name = webpath.rsplit("/", 1)[-1]
            item = Storage()
            item.webpath = webpath
            item.name = name
            items.append(item)
        row.value = ",".join(webpaths)
        row.value_list = items

        self.rows.append(row)
        return row
    

    def count_type(self, type=""):
        count = 0
        for item in self.rows:
            if item.type == type:
                count+=1
        return count
    
    def render(self):
        return xtemplate.render("common/form/form.html", form = self)
    
    @property
    def is_edit_form(self):
        return self.form_type == "edit"
    
    @property
    def is_page_edit_form(self):
        return self.form_type == FormType.page_edit
    
    @property
    def is_query_form(self):
        return self.form_type == FormType.query

class QueryForm(DataForm):
    form_type = FormType.query
    form_type_css = "query-form"
    form_method = "GET"
    footer_btn_group_css = ""

class PageEditForm(DataForm):
    form_type = FormType.page_edit
    form_type_css = "page-edit-form"
    footer_btn_group_css = ""
    delete_btn_css = "danger"

class DialogForm(DataForm):
    """弹窗表单：渲染在对话框中的编辑表单。

    DataForm 的语义化别名（form_type 同为 edit），用于和 PageEditForm（页面内联表单）
    区分，明确该表单是给弹窗场景用的。只定义表单本身，触发按钮（如 EditFormButton）
    单独使用，不要塞进表单里。
    """
    form_type = FormType.edit
    form_type_css = ""