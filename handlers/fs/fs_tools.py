# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/12/08 01:46:35
# @modified 2021/01/01 21:34:32
# -*- coding:utf-8 -*-
# @since 2018-11-22 00:46:26
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
import random
from xutils import cacheutil
from xutils.htmlutil import *
from xutils import dbutil
from xtemplate import BasePlugin

HEADER = """
<!-- 插件头部 -->
<div class="card">
    <div class="grid-title btn-line-height">
        <span>{{plugin.title}}</span>
        <div class="float-right">
            <a class="btn btn-default" href="/plugins_list">插件中心</a>
            <a class="btn btn-default" href="/fs_list">收藏夹</a>
        </div>
    </div>
</div>
"""

HTML = '''
<div class="card">
{% for note in notes %}
    <a class="list-link" href="{{note.url}}">
        <span>{{note.title}}</span>
        <div class="float-right">
            <i class="fa fa-chevron-right"></i>
        </div>
    </a>
{% end %}
</div>
'''


class Main(BasePlugin):

    title = "文件类工具"
    category = "dir"
    rows = 0
    editable = False

    def handle(self, input):
        user  = xauth.current_name()
        notes = xmanager.find_plugins("dir")

        xmanager.add_visit_log(user, "/fs_tools")
        self.writeheader(HEADER, plugin = self)
        self.writetemplate(HTML, notes = notes)
        

xurls = (
    r"/fs_tools", Main
)
