# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/12/28 22:04:24
# @modified 2021/05/01 13:45:38

# -*- coding:utf-8 -*-
# @since 2019-01-10 00:21:16
import os
import re
import math
import time
import web
import xconfig
import xutils
import xauth
import xmanager
import xtables
import xtemplate
from xtemplate import BasePlugin

HTML = """
<!-- Html -->
<style>
    .hex-text {
        font-family: monospace;
    }
</style>

<div class="card">
    <h3 class="card-title btn-line-height">
        <span>二进制查看</span>
        
        <div class="float-right">
            <a class="btn btn-default" href="/code/edit?path={{path}}">编辑本文</a>
            {% include common/button/back_button.html %}
        </div>
    </h3>
    
    {% include mod_fs_path.html %}
</div>


<div class="card">
    <textarea class="row hex-text" rows=32>{{hex_text}}</textarea>
</div>

"""

HEX_DICT = {}
for i in range(256):
    HEX_DICT[i] = '%02x ' % i

def bytes_hex(bytes):
    out = ''
    for b in bytes:
        out += HEX_DICT[b]
    return out

def bytes_chars(bytes):
    out = ''
    for b in bytes:
        c = chr(b)
        if c.isprintable():
            out += '%c' % c
        else:
            out += '.'
    return out

class Main(BasePlugin):

    show_title = False
    # 提示内容
    description = ""
    # 是否需要管理员权限
    require_admin = True
    category = 'dir'
    editable = False
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 0
        self.show_pagenation = True
        self.page_max = 0
        
        pagesize = 16 * 30
        
        path   = xutils.get_argument("path", "")
        page   = xutils.get_argument("page", 1, type = int)
        offset = max(page-1, 0) * pagesize
        
        self.page_url = "?path=%s&page=" % path
        
        if path == "":
            return
        
        path      = xutils.get_real_path(path)
        hex_text  = ""
        char_text = ""
        
        if not os.path.isfile(path):
            return "`%s` IS NOT A FILE!" % path
        else:
            filesize = xutils.get_file_size(path, format = False)
            line_fmt = "%05x"
            step = 16
            self.page_max = math.ceil(filesize / pagesize)
            padding = ' ' * 4
            with open(path, 'rb') as fp:
                fp.seek(offset)
                for i in range(0, pagesize, step):
                    bytes = fp.read(step)
                    if len(bytes) == 0:
                        break
                    hex_text += line_fmt % (offset + i)
                    hex_text += padding + bytes_hex(bytes).ljust(step * 3)
                    hex_text += padding + bytes_chars(bytes) + '\n'
            
            self.writetemplate(HTML, 
                path = path, 
                hex_text = hex_text)

    def on_init(self, context=None):
        # 插件初始化操作
        pass
    
    def command(self):
        pass

xurls = (
    r"/fs_hex", Main
)