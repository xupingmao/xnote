# -*- coding:utf-8 -*-
# @since $since
# @author $author
# @category 文件
# @title 插件名称
# @description 插件描述
# @required_role admin
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


HEADER = """
<!-- 插件头部 -->
<div class="grid-title btn-line-height">
    <span>{{plugin.title}}</span>
    <span class="float-right">
        {% if _is_admin and plugin.editable %}
            <a class="btn" href="/code/edit?path={{plugin.fpath}}">编辑</a>
        {% end %}
        <a class="btn btn-default" href="javascript:history.back();">返回</a>
    </span>
</div>
"""

BODY = """
<!-- 插件主体 -->
<p>Hello,World!</p>
"""

class Main(BasePlugin):

    title    = "Hello_World"
    category = "system"
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 0
        self.writeheader(HEADER, plugin = self)
        self.writehtml(BODY)


if __name__ == "__main__":
    # 命令行中执行
    pass

