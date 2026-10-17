import xutils
from xnote.webui.base import *
from xnote.webui import DataForm, Card, DataTable, TextContainer, ListView
from xnote.core.xtemplate import BasePlugin, LOAD_TIME
from xnote.core import xtemplate
from xnote.core import xconfig
from xutils import quote

class BasePluginV2(BasePlugin):
    rows = 0
    show_edit = False
    
    
    def handle(self, input=""):
        """按 action 字段反射派发到 handle_<action>()，未命中则交给 handle_default()"""
        action = xutils.get_argument_str("action")
        method = getattr(self, "handle_" + action, None)
        if method is not None:
            return method()
        
        self.handle_default(action)        
        
    def handle_default(self, action=""):
        self.render_error(f"功能待实现, action={action}")
        
    def add_component(self, component: BaseComponent):
        html = component.render()
        self.write_plain_html(html)
    
    def load_script(self, src: str):        
        src = xconfig.WebConfig.resolve_path(src)
        self.write_plain_html(f"""<script src="{src}"></script>""")
        
    def load_select2(self):
        self.write_plain_html(xtemplate.render("common/script/load_select2.html"))
        
    def load_laydate(self):
        self.write_plain_html(xtemplate.render("common/script/load_laydate.html"))
        
    def set_html_var(self, name: str, value):
        self.write_plain_html(f"""<input type="hidden" name="{name}" value="{quote(value)}">""")
        
        
    def add_form(self, form: DataForm):
        if form.has_select_input():
            self.load_select2()
            
        if form.has_date_input():
            self.load_laydate()
        
        self.add_component(Card().add(form))
    
    def add_table(self, table: DataTable):
        self.add_component(Card().add(table))
    
    def add_list_view(self, list_view: ListView):
        self.add_component(Card().add(list_view))
    
    def _add_pre(self, text: str, css_class=""):
        div = TextContainer(css_class="row")
        div.add_pre(text, css_class=f"my-1 border {css_class}")
        self.add_component(div)
                
    def add_error(self, text: str, css_class=""):
        self._add_pre(text=text, css_class=f"text-error {css_class}")
        
    def add_info(self, text: str, css_class=""):
        self._add_pre(text=text, css_class=f"text-info {css_class}")
        
    def add_warn(self, text: str, css_class=""):
        self._add_pre(text=text, css_class=f"text-warn {css_class}")

    # 别名
    render_form = add_form
    render_table = add_table
    render_error = add_error
    render_info = add_info
    render_warn = add_warn