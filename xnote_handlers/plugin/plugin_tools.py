import os
import xutils
import web
import base64

from xutils import Storage
from xnote.core import xconfig
from xnote.core import xauth
from xnote.core import xtemplate
from . import plugin_util
from .dao import add_visit_log
from xnote.plugin import BasePluginV2
from xnote_handlers.config import LinkConfig, AsideConfig, TabConfig
from xnote.webui import Card, Textarea, RowPanel, ActionButton, Input, Checkbox, TextSpan
from xutils import webutil
from xutils import textutil
from xutils import base62

class TccHandler:

    C_TEMPLATE = """
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char* argv) {
    printf("hello,world!");
    return 0;
}
"""

    @xauth.login_required("admin")
    def GET(self):
        code = xutils.get_argument_str("code")
        return_json = xutils.get_argument_bool("json")
        output = ""
        if code == "":
            code = self.C_TEMPLATE
        else:
            path = os.path.join(xconfig.TMP_DIR, "temp.c")
            xutils.savetofile(path, code)
            status, output = xutils.getstatusoutput("D:\\tcc\\tcc.exe -run %s" % path)

            if return_json:
                return xutils.json_str(status=status, output=output)
        return xtemplate.render("tools/tcc.html", 
            show_aside = False,
            code = code,
            output = output)
            
    def POST(self):
        return self.GET()


class LoadInnerToolHandler:

    def GET(self, name: str):
        user_name = xauth.current_name_str()
        url = "/tools/" + name
        fname = xutils.unquote(name)
        if not name.endswith(".html"):
            fname += ".html"
        # Chrome下面 tools/timeline不能正常渲染
        web.header("Content-Type", "text/html")
        fpath = os.path.join(xconfig.HANDLERS_DIR, "tools", fname)
        if os.path.exists(fpath):
            if user_name != None:
                add_visit_log(user_name, url)
            kw = Storage()
            kw.show_aside = False
            kw.parent_link = plugin_util.get_dev_link()
            return xtemplate.render("tools/" + fname, **kw)
        else:
            raise web.notfound()

    def POST(self, name):
        return self.GET(name)

class EncodeHandler(BasePluginV2):
    require_login = False
    title = "编解码工具"
    parent_link = LinkConfig.app_index
    
    def handle(self, input=""):
        encode_type = xutils.get_argument_str("type")
        event_type = xutils.get_argument_str("event_type")
        urlsafe = xutils.get_argument_str("urlsafe")
        if event_type == "click":
            return self.handle_click()
        
        self.update_aside(AsideConfig.default_aside_html)
        
        tab_card = Card()
        tab_card.add(TabConfig.encode_tab)
        
        card = Card()
        card.add(Textarea("", name="input", css_class="row", rows="10", placeholder="请输入内容"))
        btn_row = RowPanel(css_class="top-offset-1")
        btn_row.add(Input(type="hidden", name="encode_type", value=encode_type))
        btn_row.add(ActionButton(text="编码", name="encode", data_names = "input,encode_type,urlsafe"))
        btn_row.add(ActionButton(text="解码", name="decode"))
        if encode_type == "base64":
            btn_row.add(Checkbox(name="urlsafe", text="urlsafe", checked=urlsafe))
        card.add(btn_row)
        
        output_card = Card()
        output_card.add(TextSpan(id="encode-error", css_class="red"))
        output_card.add(Textarea("", name="output", css_class="row", rows="10", placeholder="编解码结果"))
        
        self.add_component(tab_card)
        self.add_component(card)
        self.add_component(output_card)
    
    def handle_click(self):
        btn_name = xutils.get_argument_str("btn_name")
        
        error_msg = ""
        output = ""
        try:
            if btn_name == "encode":
                output = self.handle_encode()
            else:
                output = self.handle_decode()
        except Exception as e:
            error_msg = str(e)
            
        result = webutil.CommandsResult()
        
        result.add_command("update_value", name="output", value=output)
        result.add_command("update_text", id="encode-error", value = error_msg)
        return result
    
    def handle_encode(self) -> str:
        input = xutils.get_argument_str("input")
        encode_type = xutils.get_argument_str("encode_type", default_value="base64")
        urlsafe = xutils.get_argument_bool("urlsafe")
        encoding = "utf-8"
                
        if encode_type == "base64":
            if urlsafe:
                return textutil.encode_base64(input)
            else:
                return base64.b64encode(input.encode(encoding)).decode(encoding)
        
        if encode_type == "base32":
            return textutil.encode_base32(input, strip=False)
        
        if encode_type == "base62":
            n = int(input)
            return base62.encode(n)
        
        raise Exception("not implemented")
    
    def handle_decode(self):
        input = xutils.get_argument_str("input")
        encode_type = xutils.get_argument_str("encode_type", default_value="base64")
        urlsafe = xutils.get_argument_bool("urlsafe")
        encoding = "utf-8"
        
        if encode_type == "base64":
            if urlsafe:
                return textutil.decode_base64(input)
            else:
                return base64.b64decode(input.encode(encoding)).decode(encoding)
        
        if encode_type == "base32":
            return textutil.decode_base32(input)
        
        if encode_type == "base62":
            return str(base62.decode(input))
            
        raise Exception("not implemented")

xurls = (
    r"/tools/tcc", TccHandler,
    r"/tools/encode", EncodeHandler,
    r"/tools/(.+)", LoadInnerToolHandler,
)