# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2019-01-10 00:21:16
@LastEditors  : xupingmao
@LastEditTime : 2022-06-12 00:29:25
@FilePath     : /xnote/handlers/fs/fs_hex.py
@Description  : 二进制查看工具
"""

import os
import math
import xutils
from xutils import Storage
from xtemplate import BasePlugin

HTML = """
<!-- Html -->
<style>
    .hex-text {
        font-family: monospace;
    }
{% if embed == "true" %}
    body {
        background-color: transparent;
    }
{% end %}

</style>

{% if embed == "true" %}
    <a class="btn btn-default" href="/code/edit?path={{path}}&embed={{embed}}">编辑本文</a>
{% else %}
    <div class="card">
        <div class="card-title btn-line-height">
            <span>二进制查看</span>
            
            <div class="float-right">
                <a class="btn btn-default" href="/code/edit?path={{path}}&embed={{embed}}">编辑本文</a>
                {% include common/button/back_button.html %}
            </div>
        </div>
    </div>
{% end %}

<div class="card">
    {% if embed == "false" %}
        {% include mod_fs_path.html %}
    {% end %}
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

        path = xutils.get_argument("path", "")
        page = xutils.get_argument("page", 1, type=int)
        offset = max(page-1, 0) * pagesize
        embed = xutils.get_argument("embed", "false")

        self.page_url = "?path={path}&embed={embed}&page=".format(path=path, embed=embed)

        if path == "":
            return

        path = xutils.get_real_path(path)
        hex_text = ""

        if not os.path.isfile(path):
            return "`%s` IS NOT A FILE!" % path
        else:
            filesize = xutils.get_file_size(path, format=False)
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

            kw = Storage()
            kw.path = path
            kw.hex_text = hex_text
            kw.embed = embed

            if embed == "true":
                self.show_nav = False

            self.writetemplate(HTML,**kw)

    def on_init(self, context=None):
        # 插件初始化操作
        pass

    def command(self):
        pass


xurls = (
    r"/fs_hex", Main
)
