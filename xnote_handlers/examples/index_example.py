# encoding=utf-8
# 演示功能入口（案例总览页），对应 /examples
from xutils import Storage
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab


class ExampleIndexHandler:
    """演示功能首页：渲染案例总览，并展示左侧导航 tab 栏。"""

    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/examples")

        kw = Storage()
        kw.title = "组件示例"
        kw.parent_link = LinkConfig.develop_index
        kw.example_tab = get_example_tab()
        return xtemplate.render("examples/page/example_index.html", **kw)

    def POST(self):
        return self.GET()


xurls = (
    r"/examples", ExampleIndexHandler,
)
