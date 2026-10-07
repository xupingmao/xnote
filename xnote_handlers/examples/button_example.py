# encoding=utf-8
# 按钮示例 tab，对应 /examples/btn
import xutils
from xutils import Storage
from xutils import webutil
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab_card, get_example_card
from xnote.plugin import BasePluginV2
from xnote.webui import RawHtml, Card, ActionButton, ConfirmButton, TextContainer, Div

_example_html = """
<button class="btn">按钮1</button>
<button class="btn btn-default">btn-default</button>
<button class="btn btn-danger">btn-danger</button>
<button class="btn danger">danger</button>
<button class="btn green">green</button>
<button class="btn pill">pill按钮</button>
<button class="btn link-style">链接样式按钮</button>
"""

class ButtonExampleHandler(BasePluginV2):
    require_login = False
    require_admin = False
    title = "组件示例"
    
    def handle_default(self, action=""):
        self.add_component(get_example_tab_card(tab_default="btn"))
        self.add_component(get_example_card(_example_html))
                
        self.add_component(ActionButton(text="toast测试", url="?action=toast"))
        self.add_component(ActionButton(text="刷新测试", url="?action=reload"))
        self.add_component(ActionButton(text="确认按钮", confirm_msg="确认执行吗?", url="?action=confirm"))
        self.add_component(ActionButton(text="更新HTML", url="?action=update_html"))
        
        output = TextContainer()
        output.add_span(text="输出", css_class="card-title")
        output.add(Div(id="html-output", css_class="card p-2", html="-"))
        self.add_component(output)
    
    def handle_toast(self):
        result = webutil.CommandsResult()
        result.add_command(command="toast", value="toast测试")
        return result
    
    def handle_reload(self):
        result = webutil.CommandsResult()
        result.add_toast_command(value="500毫秒后刷新")
        result.add_reload_command()
        return result
    
    def handle_confirm(self):
        result = webutil.CommandsResult()
        result.add_toast_command(value="服务端已经执行")
        return result
    
    def handle_update_html(self):
        html = f"服务器时间: {xutils.format_datetime()} <a>EmptyLink</a>"
        result = webutil.CommandsResult()
        result.add_command(command="update_html", id="html-output", value=html)
        return result

xurls = (
    r"/examples/btn", ButtonExampleHandler,
)
