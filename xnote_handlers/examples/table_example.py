# encoding=utf-8
# Table 示例 tab，对应 /examples/table
import xutils
import copy

from xutils import Storage
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.core import xconfig
from xnote.plugin.table_plugin import BaseTablePlugin, BasePlugin
from xnote.plugin import DataTable, TableActionType, TabBox, QueryForm, TabTable, DataForm, PageEditForm, DialogForm, EditFormButton
from xnote.plugin.form_plugin import BaseFormPlugin
from xnote.webui import Card, FormRowType
from xnote.plugin.table import InfoTable, InfoItem, ActionBar, TableRowType
from xnote.webui import ListView, ListItem, ConfirmButton, TextTag
from xutils import textutil
from xutils import webutil
from xutils.number_util import IntCounter
from xutils.db.dbutil_cache import DatabaseCache
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab

# 注意：from .example_handler import get_example_tab 已迁移到 example_nav.py

# kv_cache 单例（延迟初始化，避免模块导入阶段触碰数据库表）
_KV_CACHE = None

def get_kv_cache():
    global _KV_CACHE
    if _KV_CACHE is None:
        _KV_CACHE = DatabaseCache()
    return _KV_CACHE

# 缓存有效期：30 天（编辑保存时重新 put 即续期）
TTL_SECONDS = 30 * 24 * 3600


def _type_info(type_code):
    """类型编码 -> (展示名, 配色class)"""
    return {
        "1": ("类型1", "red"),
        "2": ("类型2", "green"),
    }.get(type_code, ("类型1", "red"))


class TableExampleHandler(BaseTablePlugin):

    parent_link = LinkConfig.develop_index

    title = "表格测试"

    show_aside = False

    heading_count = IntCounter()

    PAGE_HTML = """
{% include examples/component/example_nav_tab.html %}

<div class="card">
    {% render tab %}
    {% render tab2 %}
</div>

<div class="card">
    {% render info_table %}
</div>

<div class="card">
    {% render query_form %}
</div>

<div class="card">
    {% include common/table/table.html %}
</div>

<div class="card">
    {% set-global xnote_table_var = "weight_table" %}
    {% include common/table/table_v2.html %}
</div>

<div class="card">
    {% render empty_table %}
</div>

<div class="card">
    {% render image_table %}
</div>
"""

    tab_title_width = "120px"

    # ------------------------------------------------------------------
    # kv_cache 持久化（主数据表，一个用户一条大 JSON）
    # ------------------------------------------------------------------
    KV_PREFIX = "examples_table"

    def _kv_key(self):
        return f"{self.KV_PREFIX}:{xauth.current_user_id()}"

    def _load_records(self):
        data = get_kv_cache().get(self._kv_key(), default_value={"records": []})
        if not isinstance(data, dict):
            return []
        return data.get("records", []) or []

    def _save_records(self, records):
        # 编辑保存时重新 put，expire_time 刷新即续期
        get_kv_cache().put(self._kv_key(), {"records": records}, expire=TTL_SECONDS)

    def _seed_if_empty(self):
        """首次访问（缓存为空）时写入示例数据"""
        if len(self._load_records()) > 0:
            return
        seed = [
            {"id": 1, "type": "1", "title": "测试", "date": "2020-01-01", "content": "测试内容"},
            {"id": 2, "type": "2", "title": "示例记录", "date": "2020-06-15", "content": "这是一条示例记录"},
        ]
        for r in seed:
            name, css_class = _type_info(r["type"])
            r["type_name"] = name
            r["type_class"] = css_class
        self._save_records(seed)

    def handle_page(self):
        self._seed_if_empty()
        records = self._load_records()

        table = DataTable()
        table.title = "表格1-自动宽度（持久化）"
        table.add_head("类型", "type", css_class_field="type_class")
        table.add_head("标题", "title", link_field="view_url")
        table.add_head("日期", "date")
        table.add_head("内容", "content")

        # 编辑：普通链接跳转（导航到 FormPlugin 编辑页）；删除：确认后调用 FormPlugin
        table.add_action("编辑", link_field="edit_url", type=TableActionType.link, css_class="btn default")
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm,
                         msg_field="delete_msg", css_class="btn danger")

        # 操作栏：新建记录（导航到 FormPlugin 编辑页）
        table.action_bar.add_span("FormPlugin编辑页", css_class="pl-1 bold")
        table.action_bar.add_link("新建记录", "/examples/table/edit", css_class="btn", float_right=True)

        for rec in records:
            row = {}
            row["id"] = rec.get("id")
            row["type"] = rec.get("type_name", _type_info(rec.get("type", "1"))[0])
            row["type_class"] = rec.get("type_class", _type_info(rec.get("type", "1"))[1])
            row["title"] = rec.get("title", "")
            row["date"] = rec.get("date", "")
            row["content"] = rec.get("content", "")
            row["view_url"] = "/note/index"
            row["edit_url"] = "/examples/table/edit?id=%s" % rec.get("id")
            row["delete_url"] = "/examples/table/edit?action=delete&id=%s" % rec.get("id")
            row["delete_msg"] = "确认删除记录[%s]吗?" % rec.get("title", "")
            table.add_row(row)

        # 分页直接设置到表格组件上, 表格底部会自动渲染分页
        page_total = max(1, (len(records) + 19) // 20)
        table.set_pagination(page=1, page_total=page_total, page_size=20)

        kw = Storage()
        kw.table = table

        kw.query_form = self.get_query_form()
        kw.weight_table = self.get_weight_table()
        kw.empty_table = self.get_empty_table()
        kw.tab = self.get_tab_component()
        kw.tab2 = self.get_tab2()
        kw.example_tab = get_example_tab(tab_default="table")
        kw.info_table = self.get_info_table()
        kw.image_table = self.get_image_table()

        return self.response_page(**kw)

    # 保留：弹窗表单示例（供 weight_table / empty_table 的「新建」按钮演示用）
    def handle_edit(self):
        self.heading_count.add(1)
        show_heading = xutils.get_argument_bool("show_heading", True)

        form = self.create_form()

        if show_heading:
            form.add_heading("基础信息")

        form.add_row("id", "id", css_class="hide")
        form.add_row("只读属性", "readonly_attr", value="test", readonly=True)

        row = form.add_row("类型", "type", type=self.FormRowType.select)
        row.add_option("类型1", "1")
        row.add_option("类型2", "2")

        form.add_row("标题", "title")
        form.add_row("日期", "date", type=self.FormRowType.date)
        form.add_row("内容", "content", type=self.FormRowType.textarea)

        if show_heading:
            form.add_heading("高级信息")

        row = form.add_select("标签", field="tags", multiple=True, value=[1,2])
        row.add_option("标签1", "1")
        row.add_option("标签2", "2")
        row.add_option("标签3", "3")

        row = form.add_tag_select("标签(tag风格-单选)", field="tags2", value="1")
        row.add_option("标签1", "1")
        row.add_option("标签2", "2")
        row.add_option("标签3", "3")

        row = form.add_tag_select("标签(tag风格-多选)", field="tags3", multiple=True, value=["1", "2"])
        row.add_option("标签1", "1")
        row.add_option("标签2", "2")
        row.add_option("标签3", "3")

        form.add_row("备注信息")

        form.add_image("封面图片", "cover")
        form.add_file("附件", "attachments", multiple=True)

        kw = Storage()
        kw.form = form
        return self.response_form(**kw)

    def handle_save(self):
        data_dict = self.get_param_dict()
        return webutil.FailedResult(code="500", message=f"data_dict={data_dict}")

    def get_tab_component(self):
        tab = TabBox(
            tab_key="tab", tab_default="2", css_class="btn-style",
            title="后端tab组件", title_width=self.tab_title_width)
        tab.add_tab(title="选项1", value="1", href="?tab=1")
        tab.add_tab(title="选项2", value="2")
        tab.add_tab(title="选项3", value="3", css_class="hide")
        tab.add_tab(title="onclick", href="#", onclick="javascript:alert('onclick!')")
        return tab

    def get_tab2(self):
        tab = TabBox(
            tab_key="tab2", css_class="btn-style",
            title="状态", title_width=self.tab_title_width)
        tab.add_tab(title="正常", value="1")
        tab.add_tab(title="停用", value="2")
        return tab

    def get_query_form(self):
        type_str = xutils.get_argument_str("type")
        keyword = xutils.get_argument_str("keyword")
        date_str = xutils.get_argument_str("date")

        form = QueryForm()
        row = form.add_select(title="类型", field="type", value=type_str)
        row.add_option("类型-1", "1")
        row.add_option("类型-2", "2")
        form.add_row(title="关键字", field="keyword", value=keyword)
        form.add_date_input(title="日期", field="date", value=date_str)

        return form

    def get_weight_table(self):
        table = DataTable()
        table.title = "表格2-权重宽度"
        table.add_head("权重1", field="value1", width_weight=1)
        table.add_head("权重1", field="value2", width_weight=1)
        table.add_head("权重2", field="value3", width_weight=2)
        table.add_head("权重1", field="value4", width_weight=1)
        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm,
                         msg_field="delete_msg", css_class="btn danger")

        row = {}
        row["value1"] = "value1"
        row["value2"] = "value2"
        row["value3"] = "value3"
        row["value4"] = "value4"
        row["view_url"] = "/note/index"
        row["edit_url"] = "?action=edit"
        row["delete_url"] = "?action=delete"
        row["delete_msg"] = "确认删除记录吗?"

        table.add_row(row)
        return table

    def get_empty_table(self):
        table = DataTable()
        table.add_head("权重1", field="value1", width_weight=1)
        table.add_head("权重1", field="value2", width_weight=1)
        table.add_head("权重2", field="value3", width_weight=2)
        table.add_head("权重1", field="value4", width_weight=1)
        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm,
                         msg_field="delete_msg", css_class="btn danger")

        action_bar = table.action_bar
        action_bar.add_span(text="表格3-action_bar")
        action_bar.add_edit_button(text="新建", url="?action=edit", float_right=True)
        return table

    def get_info_table(self):
        table = InfoTable()
        table.cols = xutils.get_argument_int("cols", 2)
        table.add_item(InfoItem(name="组件名称", value="信息表格"))
        table.add_item(InfoItem(name="用途", value="展示对象的详细信息"))
        table.add_item(InfoItem(name="链接", value="xnote首页", href="/"))
        table.add_item(InfoItem(name="其他"))
        table.bottom_action_bar.add_edit_button("编辑1", "?action=edit&show_heading=true", css_class="btn-default")
        table.bottom_action_bar.add_edit_button("编辑2", "?action=edit&show_heading=false", css_class="btn-default")
        table.bottom_action_bar.add_confirm_button("删除", url="?action=delete", message="确认删除吗?", css_class="danger")
        return table

    def get_image_table(self):
        server_home = xconfig.WebConfig.server_home

        def image_url(path):
            return server_home + "/_static/" + path

        table = DataTable()
        table.title = "表格-图片类型"
        table.add_head("名称", "name")
        table.add_image_head("图标", "icon")
        table.add_head("说明", "desc")

        rows = [
            ("文件", "image/file.png", "普通文件图标"),
            ("文件夹", "image/folder2.png", "文件夹图标"),
            ("搜索", "image/icon_search.png", "搜索图标"),
            ("词典", "image/icon_dict.png", "词典图标"),
            ("游戏", "image/icons/icon_game.png", "游戏图标"),
            ("XNote", "xnote.png", "XNote 图标"),
            ("Favicon", "favicon.ico", "网站图标"),
        ]
        for name, path, desc in rows:
            table.add_row({"name": name, "icon": image_url(path), "desc": desc})
        return table


class TableExampleFormHandler(BaseFormPlugin):
    """表格示例的编辑页（基于 BaseFormPlugin，纯组件渲染）"""

    title = "表格记录编辑"
    parent_link = LinkConfig.develop_index
    show_aside = False

    KV_PREFIX = "examples_table"

    def _kv_key(self):
        return f"{self.KV_PREFIX}:{xauth.current_user_id()}"

    def _load_records(self):
        data = get_kv_cache().get(self._kv_key(), default_value={"records": []})
        if not isinstance(data, dict):
            return []
        return data.get("records", []) or []

    def _save_records(self, records):
        # 编辑保存时重新 put，expire_time 刷新即续期
        get_kv_cache().put(self._kv_key(), {"records": records}, expire=TTL_SECONDS)

    def _find_record(self, record_id):
        if not record_id:
            return {}
        for rec in self._load_records():
            if str(rec.get("id")) == str(record_id):
                return rec
        return {}

    def handle_edit(self):
        record_id = xutils.get_argument_str("id")
        record = self._find_record(record_id)

        # 页面内编辑表单（带保存/删除按钮），提交到当前路由的 save/delete
        form = PageEditForm()
        form.path = "/examples/table/edit"
        form.model_name = "table_example"
        form.add_row("id", "id", css_class="hide", value=record_id)
        form.add_row("只读属性", "readonly_attr", value="test", readonly=True)

        row = form.add_select("类型", "type", value=record.get("type", "1"))
        row.add_option("类型1", "1")
        row.add_option("类型2", "2")

        form.add_row("标题", "title", value=record.get("title", ""))
        form.add_date_input("日期", "date", value=record.get("date", ""))
        form.add_row("内容", "content", type=FormRowType.textarea, value=record.get("content", ""))

        if record_id:
            form.delete_url = "/examples/table/edit?action=delete&id=%s" % record_id
        else:
            form.delete_url = "/examples/table/edit?action=delete"
        form.delete_reload_href = "/examples/table"

        self.render_form(form)

    def handle_save(self):
        data = self.get_data_dict()
        records = self._load_records()
        record_id = data.get("id", "")

        name, css_class = _type_info(data.get("type", "1"))
        new_record = {
            "id": record_id,
            "type": data.get("type", "1"),
            "type_name": name,
            "type_class": css_class,
            "title": data.get("title", ""),
            "date": data.get("date", ""),
            "content": data.get("content", ""),
        }

        if record_id:
            for rec in records:
                if str(rec.get("id")) == str(record_id):
                    rec.update(new_record)
                    break
        else:
            new_id = max([int(r.get("id", 0)) for r in records], default=0) + 1
            new_record["id"] = new_id
            records.append(new_record)

        self._save_records(records)
        return webutil.SuccessResult(message="保存成功", redirect_url="/examples/table")

    def handle_delete(self):
        record_id = xutils.get_argument_str("id")
        if not record_id:
            # 列表/表格的确认删除是 GET（无 data 体），编辑页表单删除带 data 体
            try:
                data = self.get_data_dict()
                record_id = data.get("id", "")
            except Exception:
                record_id = ""
        if not record_id:
            return webutil.FailedResult(code="400", message="缺少记录ID")

        records = [r for r in self._load_records() if str(r.get("id")) != str(record_id)]
        self._save_records(records)
        return webutil.SuccessResult(message="删除成功")


xurls = (
    # 更具体的子路由放前面，避免被 /examples/table 的(.*)前缀匹配抢先
    r"/examples/table/edit", TableExampleFormHandler,
    r"/examples/table", TableExampleHandler,
)
