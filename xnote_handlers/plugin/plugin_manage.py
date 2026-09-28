
import os
import xutils
from xnote.core import xauth, xconfig
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote_handlers.config import LinkConfig
from xutils import Storage, dateutil
from xutils import fsutil, webutil
from xnote.plugin.table import TableActionType
from xnote.plugin import iter_plugins, TabBox
from .dao import delete_visit_log
from .plugin_page import list_all_plugins, list_plugins
from .plugin_config import CategoryService
from xnote_handlers.config import AsideConfig
from xnote.webui import Card

class PluginManageHandler(BaseTablePlugin):
    title = "插件管理"
    parent_link = LinkConfig.plugin_index
    require_admin = True
    show_pagenation = False
    NAV_HTML = ""

    def handle_page(self):
        self.update_aside(AsideConfig.default_aside_html)
        
        filter_tab = TabBox(tab_key="category", tab_default="all")

        for category in CategoryService.category_list:
            filter_tab.add_tab(title=category.name, value=category.code)

        self.add_component(Card().add(filter_tab))

        category = xutils.get_argument_str("category")

        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head("插件类别", "category_list")
        table.add_head("插件ID", "plugin_id")
        table.add_head("插件名称", "title", link_field="view_url")
        table.add_head("最近使用", "visit_date")
        table.add_head("访问次数", "visit_cnt")

        table.add_action("编辑", link_field="edit_url", type=TableActionType.link, css_class="btn btn-default")
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm,
                         msg_field="delete_msg", css_class="btn danger")
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
            row["plugin_id"] = plugin.plugin_id
            row["delete_url"] = "?action=delete&plugin_name=" + xutils.encode_uri_component(plugin.plugin_name)
            row["delete_msg"] = "确定删除插件[%s]吗? 插件文件会移动到回收站" % plugin.title
            table.add_row(row)

        kw = Storage()
        kw.table = table
        return self.response_page(**kw)

    def handle_delete(self):
        """删除插件: 把插件文件移动到回收站, 并同步移除内存中已注册的插件"""
        plugin_name = xutils.get_argument_str("plugin_name")
        if plugin_name == "":
            return webutil.FailedResult(message="缺少参数plugin_name")

        plugin = xconfig.PLUGINS_DICT.get(plugin_name)
        if plugin is None:
            return webutil.FailedResult(message="插件[%s]不存在" % plugin_name)
        if plugin.is_builtin:
            return webutil.FailedResult(message="内置插件不支持删除")

        # 插件目录是唯一的合法删除范围, 避免删除插件目录以外的文件
        fpath = os.path.abspath(plugin.fpath)
        if not fsutil.is_parent_dir(xconfig.PLUGINS_DIR, fpath):
            return webutil.FailedResult(message="非法的插件路径:%s" % plugin.fpath)

        # 软删除, 文件默认移动到回收站
        fsutil.remove_file(fpath)
        delete_visit_log(user_name=xauth.current_name_str(), url="/plugin/" + plugin_name)
        # 同步移除, 插件列表和 /plugin/<name> 立即生效
        xconfig.PLUGINS_DICT.pop(plugin_name, None)

        return webutil.SuccessResult(message="插件[%s]已删除" % plugin.title)

xurls = (
    "/plugin_manage", PluginManageHandler,
)
