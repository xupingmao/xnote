# -*- coding:utf-8 -*-
# @since 2026/09/19
# 开发者工具宫格导航页面（参考 xnote_handlers/system/system_index.py 应用中心）
"""Developer tools grid navigation page"""
import xutils

from xnote.core import xauth
from xutils import Storage
from xnote.plugin.grid import AppGrid, AppInfo
from xnote.plugin import BasePlugin
from xnote_handlers.config import LinkConfig, AsideConfig


# 开发者工具分类（宫格项），URL 取自 plugin_config.py 中的 dev_plugin 注册
DEVELOPER_APPS = [
    AppInfo(name="浏览器信息", url="/tools/browser_info",                 icon="globe"),
    AppInfo(name="图片工具",   url="/tools/img_merge?tab=merge&nav=true", icon="image"),
    AppInfo(name="编解码工具", url="/tools/encode?tab=BASE64&nav=true",    icon="exchange"),
    AppInfo(name="文本工具",   url="/tools/text_convert?tab=convert&nav=true", icon="file-text-o"),
    AppInfo(name="前端组件",   url="/examples",                    icon="cubes"),
    AppInfo(name="系统模块",   url="/system/module_list",                 icon="sitemap"),
    AppInfo(name="性能分析",   url="/system/handler_profile",             icon="tachometer"),
]


class DeveloperHandler(BasePlugin):

    title = "开发者"
    require_login = True
    require_admin = True
    rows = 0

    def handle(self, input=""):
        arg_show_back = xutils.get_argument_bool("show_back")
        arg_show_menu = xutils.get_argument_bool("show_menu", default_value=True)

        self.show_back = arg_show_back
        self.show_nav = arg_show_menu

        # 上级功能链接：应用中心
        self.parent_link = LinkConfig.app_index

        # 标题栏右侧：返回按钮 + 插件入口
        self.option_html = (
            LinkConfig.plugin_index_btn.render()
            + " "
            + '<a class="btn btn-default" href="javascript:history.back();">返回</a>'
        )

        app_grid = AppGrid(css_class="card")
        for app in DEVELOPER_APPS:
            app_grid.add_app(app)

        self.writehtml(app_grid.render(), _do_render=False)
        self.write_aside(AsideConfig.note_aside_html)


xutils.register_func("url:/system/develop", DeveloperHandler)

xurls = (
    r"/system/develop", DeveloperHandler,
)
