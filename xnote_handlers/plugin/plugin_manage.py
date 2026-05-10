
import xutils
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote_handlers.config import LinkConfig
from xutils import Storage, dateutil
from xnote.core import xauth
from xnote.plugin.table import TableActionType
from xnote.plugin import iter_plugins, TabBox
from .plugin_page import list_all_plugins, list_plugins
from .plugin_config import CategoryService
from xnote_handlers.config.aside_config import AsideConfig

class PluginManageHandler(BaseTablePlugin):
    title = "插件管理"
    parent_link = LinkConfig.plugin_index
    require_admin = True
    show_pagenation = False
    NAV_HTML = ""

    filter_tab_html = """
<div class="card">
    {% render filter_tab %}
</div>
"""

    def handle_page(self):
        self.update_aside(AsideConfig.get_default_aside_html())
        
        filter_tab = TabBox(tab_key="category", tab_default="all")

        for category in CategoryService.category_list:
            filter_tab.add_tab(title=category.name, value=category.code)

        self.writetemplate(self.filter_tab_html, filter_tab = filter_tab)

        category = xutils.get_argument_str("category")

        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head("插件类别", "category_list")
        table.add_head("插件名称", "title", link_field="view_url")
        table.add_head("最近使用", "visit_date")
        table.add_head("访问次数", "visit_cnt")

        table.add_action("编辑", link_field="edit_url", type=TableActionType.link, css_class="btn btn-default")
        table.action_bar.add_edit_button(text="新增插件", url="?action=edit")
        table.action_bar.add_link(text="查看插件目录", href="/fs_link/scripts/plugins", css_class="btn btn-default")

        for plugin in list_plugins(category=category):
            if plugin.is_builtin:
                # 不管理内置的工具
                continue

            row = {}
            row["category_list"] = ",".join(plugin.category_list)
            row["title"] = plugin.title
            row["visit_date"] = dateutil.format_date(plugin.visit_time)
            row["visit_cnt"] = plugin.visit_cnt
            row["view_url"] = plugin.abs_url
            row["edit_url"] = plugin.edit_link
            table.add_row(row)

        kw = Storage()
        kw.table = table
        return self.response_page(**kw)

xurls = (
    "/plugin_manage", PluginManageHandler,
)