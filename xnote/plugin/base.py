from xnote.webui.base import *
from xnote.core.xtemplate import BasePlugin, LOAD_TIME
from xnote.core import xtemplate
from xnote.core import xconfig
from xutils import quote

class BasePluginV2(BasePlugin):
    rows = 0
    show_edit = False
        
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
