# encoding=utf-8
# Switch 示例 tab，对应 /examples/switch
from xutils import Storage
from xutils import webutil
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.plugin import Switch
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab


class SwitchExampleHandler:
    """开关组件示例

    GET 展示各种用法；POST 演示开关在表单里的提交（提交后回显收到的值）。
    """

    # 表单演示的字段，提交值取自隐藏域，未打开时取到 off_value
    FORM_FIELDS = ("enabled", "notify")

    def GET(self):
        return self.render_page(result="")

    def POST(self):
        result = "提交结果: " + ", ".join(
            [f"{field}={webutil.get_argument_str(field, '')}" for field in self.FORM_FIELDS])
        return self.render_page(result=result)

    def render_page(self, result=""):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/examples/switch")

        kw = Storage()
        kw.title = "组件示例"
        kw.parent_link = LinkConfig.develop_index
        kw.example_tab = get_example_tab(tab_default="switch")
        kw.result = result

        # 基础用法
        kw.switch_basic = Switch(name="demo_basic", text="默认关闭")
        kw.switch_checked = Switch(name="demo_checked", text="默认开启", checked=True)
        kw.switch_no_text = Switch(name="demo_no_text", checked=True)
        kw.code_basic = 'Switch(name="enabled", text="默认关闭")\n' \
                        'Switch(name="enabled", text="默认开启", checked=True)'

        # 尺寸
        kw.switch_sm = Switch(name="demo_sm", text="小号", size="sm", checked=True)
        kw.switch_lg = Switch(name="demo_lg", text="大号", size="lg", checked=True)
        kw.code_size = 'Switch(name="size", text="小号", size="sm")\n' \
                       'Switch(name="size", text="大号", size="lg")'

        # 禁用
        kw.switch_disabled = Switch(name="demo_disabled", text="禁用(关闭)", disabled=True)
        kw.switch_disabled_on = Switch(name="demo_disabled_on", text="禁用(开启)",
                                       checked=True, disabled=True)
        kw.code_disabled = 'Switch(name="enabled", text="禁用", disabled=True)'

        # 自定义提交值
        kw.switch_custom = Switch(name="demo_custom", text="自定义值(1/0)",
                                  checked=True, on_value="1", off_value="0")
        kw.code_custom = 'Switch(name="enabled", on_value="1", off_value="0")'

        # 表单提交：用提交上来的值回填，演示服务端如何取值
        kw.form_enabled = Switch(name="enabled", text="启用",
                                 checked=webutil.get_argument_str("enabled", "false"))
        kw.form_notify = Switch(name="notify", text="消息通知",
                                checked=webutil.get_argument_str("notify", "false"))
        kw.code_form = 'Switch(name="enabled", text="启用", checked=enabled)\n' \
                       '# 服务端取值: webutil.get_argument_str("enabled", "false")\n' \
                       '# DataForm 表单行: form.add_switch(title="启用", field="enabled", checked=True)'

        return xtemplate.render("examples/page/example_switch.html", **kw)


xurls = (
    r"/examples/switch", SwitchExampleHandler,
)
