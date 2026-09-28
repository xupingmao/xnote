
import json
import os
import xutils
from xnote.core import xauth, xconfig, xtemplate
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


def build_meta_dict(plugin) -> dict:
    """把插件的meta信息整理成dict, 用于以JSON展示

    - 单值字段保持字符串
    - 出现多次的字段(比如写了多个 @category)聚合为list
    """
    meta = plugin.meta
    result = dict(meta.meta_dict)
    for key, values in meta.meta_list_dict.items():
        if len(values) > 1:
            result[key] = values

    return {
        "plugin_name": plugin.plugin_name,
        "fpath": plugin.fpath,
        "meta": result,
    }


class PluginManageHandler(BaseTablePlugin):
    title = "插件管理"
    parent_link = LinkConfig.plugin_index
    require_admin = True
    show_pagenation = False
    NAV_HTML = ""

    # 「查看meta」点击后拉取纯文本JSON, 用文本弹窗展示(不跳转页面)
    VIEW_META_SCRIPT = """
<script>
$(document).on("click", ".plugin-meta-btn", function (event) {
    event.preventDefault();
    var url = $(this).attr("href");
    xnote.http.get(url, function (text) {
        xnote.showTextDialog("插件meta", text);
    });
});
</script>
"""

    def handle_page(self):
        self.update_aside(AsideConfig.default_aside_html)
        self.write_plain_html(self.VIEW_META_SCRIPT)

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
        table.add_action("查看meta", link_field="meta_url", type=TableActionType.link,
                         css_class="btn btn-default plugin-meta-btn")
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
            row["meta_url"] = "?action=meta&plugin_name=" + xutils.encode_uri_component(plugin.plugin_name)
            row["delete_url"] = "?action=delete&plugin_name=" + xutils.encode_uri_component(plugin.plugin_name)
            row["delete_msg"] = "确定删除插件[%s]吗? 插件文件会移动到回收站" % plugin.title
            table.add_row(row)

        kw = Storage()
        kw.table = table
        return self.response_page(**kw)

    def json_text_response(self, data: dict):
        """以纯文本JSON返回, 前端用文本弹窗展示"""
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return xtemplate.TextResponse(text)

    def handle_meta(self):
        """查看插件meta信息, 以纯文本JSON展示"""
        plugin_name = xutils.get_argument_str("plugin_name")
        if plugin_name == "":
            return self.json_text_response(dict(success=False, message="缺少参数plugin_name"))

        plugin = xconfig.PLUGINS_DICT.get(plugin_name)
        if plugin is None:
            return self.json_text_response(dict(success=False, message="插件[%s]不存在" % plugin_name))

        result = dict(success=True)
        result.update(build_meta_dict(plugin))
        return self.json_text_response(result)

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
