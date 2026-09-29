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
from xnote.webui import FormRowType, Card
from xnote.webui import ActionBar
from xnote.plugin import PageEditForm
from xnote.plugin.form_plugin import BaseFormPlugin
from xnote.core import xauth
from xutils.db.dbutil_cache import DatabaseCache

# kv_cache 单例（延迟初始化，避免模块导入阶段触碰数据库表）
_KV_CACHE = None

def get_kv_cache():
    global _KV_CACHE
    if _KV_CACHE is None:
        _KV_CACHE = DatabaseCache()
    return _KV_CACHE

# 缓存有效期：30 天（编辑保存时重新 put 即续期）
TTL_SECONDS = 30 * 24 * 3600


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

    # ------------------------------------------------------------------
    # kv_cache 持久化（列表数据，一个用户一条大 JSON）
    # ------------------------------------------------------------------
    KV_PREFIX = "examples_list"

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
        if len(self._load_records()) > 0:
            return
        seed = [
            {"id": 1, "title": "标题 - row1", "content": "说明XXX", "date": "2020-01-01"},
            {"id": 2, "title": "标题 - row2", "content": "说明YYY", "date": "2020-03-12"},
            {"id": 3, "title": "标题 - row3", "content": "说明ZZZ", "date": "2020-05-20"},
        ]
        self._save_records(seed)

    def handle_page(self):
        self._seed_if_empty()
        records = self._load_records()

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
        list_view.action_bar.add_css_class("border-b")
        list_view.action_bar.add_span("操作栏", css_class="pl-1 bold pr-1")
        list_view.action_bar.add_link(text = "新增记录", href="/examples/list_plugin/edit", css_class="btn")
        list_view.action_bar.extra.add_link(text = "新增记录", href="/examples/list_plugin/edit", css_class="btn")
        list_view.action_bar.extra.add_confirm_button(text="帮助", message="仅用于占位", css_class="btn-default")

        now = dateutil.format_date()

        for rec in records:
            text = rec.get("title", "")
            list_item = ListViewItem(
                icon_class="fa fa-file-text-o",
                show_chevron_right=True)
            
            list_item.add_span(text=text, css_class="bold")
            list_item.add_br()
            list_item.add_span(rec.get("content", ""), css_class="gray")
            list_item.add_br()

            list_item.add_span(f"更新于 {rec.get('date', now)}", css_style="color:#999;")
            list_item.add_item_sep()
            list_item.add_span("标签", css_class="gray")

            # 编辑：普通链接跳转（导航到 FormPlugin 编辑页）
            list_item.extra.add_link(text="编辑", href="/examples/list_plugin/edit?id=%s" % rec.get("id"), css_class="btn btn-default")
            # 删除：确认后调用 FormPlugin（破坏性操作链接用红色，见 AGENTS.md）
            list_item.extra.add_confirm_button(
                text="删除",
                url="/examples/list_plugin/edit?action=delete&id=%s" % rec.get("id"),
                message=f"确认删除[{text}]吗?",
                css_class="btn danger")

            list_view.add_item(list_item)

        page = xutils.get_argument_int("page", 1)

        # 分页直接设置到列表组件上, 列表底部会自动渲染分页
        page_total = max(1, (len(records) + 19) // 20)
        list_view.set_pagination(page=page, page_total=page_total, page_size=20)

        kw = Storage()
        kw.list_view = list_view

        self.writehtml(
            self.tab_html,
            tab1=tab1,
            tab2=tab2,
            example_tab=get_example_tab(tab_default="list_plugin"))
        return self.response_page(**kw)


class ListPluginFormHandler(BaseFormPlugin):
    """ListPlugin 示例的编辑页（基于 BaseFormPlugin，纯组件渲染）"""

    title = "列表记录编辑"
    parent_link = LinkConfig.develop_index
    show_aside = False

    KV_PREFIX = "examples_list"

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

        form = PageEditForm()
        form.path = "/examples/list_plugin/edit"
        form.model_name = "list_plugin_example"
        form.add_row("id", "id", css_class="hide", value=record_id)
        form.add_row("标题", "title", value=record.get("title", ""))
        form.add_date_input("日期", "date", value=record.get("date", ""))
        form.add_row("内容", "content", type=FormRowType.textarea, value=record.get("content", ""))

        if record_id:
            form.delete_url = "/examples/list_plugin/edit?action=delete&id=%s" % record_id
        else:
            form.delete_url = "/examples/list_plugin/edit?action=delete"
        form.delete_reload_href = "/examples/list_plugin"

        self.render_form(form)

    def handle_save(self):
        data = self.get_data_dict()
        records = self._load_records()
        record_id = data.get("id", "")

        new_record = {
            "id": record_id,
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
        return webutil.SuccessResult(message="保存成功", redirect_url="/examples/list_plugin")

    def handle_delete(self):
        record_id = xutils.get_argument_str("id")
        if not record_id:
            # 列表的确认删除是 GET（无 data 体），编辑页表单删除带 data 体
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
    # 更具体的子路由放前面，避免被 /examples/list_plugin 的(.*)前缀匹配抢先
    r"/examples/list_plugin/edit", ListPluginFormHandler,
    r"/examples/list_plugin", ListPluginHandler,
)
