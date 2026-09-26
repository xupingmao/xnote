# encoding=utf-8
# 路由插件(BaseRouterPlugin)示例 tab，对应 /examples/router
import xutils

from typing import Optional
from xutils import Storage
from xutils import dateutil
from xnote.plugin import BasePluginV2, BaseRouterPlugin, PluginContext
from xnote.webui import TextSpan
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab


class HelloView(BasePluginV2):
    """子视图: 精确匹配 action=hello"""

    def handle(self, input=""):
        self.add_component(TextSpan(text="匹配到路由 action=hello，这是 HelloView 渲染的内容"))


class TimeView(BasePluginV2):
    """子视图: 匹配 action=time (re.match 是前缀匹配, time/timezone 都会命中)"""

    def handle(self, input=""):
        self.add_component(TextSpan(text=f"匹配到路由 action=time*，当前时间 {dateutil.format_datetime()}"))


class SearchView(BasePluginV2):
    """子视图: 正则匹配 action=search.*，业务参数自己从 query 里取"""

    def handle(self, input=""):
        key = xutils.get_argument_str("key")
        self.add_component(TextSpan(text=f"匹配到路由 action=search.*，搜索关键词 key={key}"))


class DefaultView(BasePluginV2):
    """子视图: 兜底页面 (所有路由都未命中时)"""

    def handle(self, input=""):
        self.add_component(TextSpan(text="未匹配到任何路由，展示默认页面"))


class RouterDemoPlugin(BaseRouterPlugin):
    """演示用的路由插件: 通过 action 参数把请求分发到不同的子视图"""

    title = "路由插件示例"
    # 每个路由插件子类定义自己的路由表, 避免多个子类共享基类的列表
    handlers = []

    def on_init(self, context: Optional[PluginContext] = None):
        self.add_handler(r"hello", HelloView)
        self.add_handler(r"time", TimeView)
        self.add_handler(r"search.*", SearchView)
        # 所有路由都未命中时的兜底视图
        self.default_handler = DefaultView


class RouterExampleHandler:

    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/examples/router")

        plugin = RouterDemoPlugin()
        plugin.on_init()
        plugin.handle()

        kw = Storage()
        kw.title = "组件示例"
        kw.parent_link = LinkConfig.develop_index
        kw.example_tab = get_example_tab(tab_default="router")
        kw.action = xutils.get_argument_str("action", "")
        kw.router_html = plugin.html
        return xtemplate.render("examples/page/example_router.html", **kw)

    def POST(self):
        return self.GET()


xurls = (
    r"/examples/router", RouterExampleHandler,
)
