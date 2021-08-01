# -*- coding:utf-8 -*-
# @api_level 2.8
# @since $since
# @author $author
# @version 1.0.0
# @category note
# @title 插件名称
# @description 插件描述
# @required_role admin
# @tags system test
# @enabled
# @icon_class fa-cube
import os
import re
import math
import time
import web
import xconfig
import xutils
import xauth
import xmanager
import xtemplate
from xtemplate import BasePlugin

BODY_HTML = """
<!-- 插件主体 -->
<div class="card">
    <p>Hello,World!</p>
</div>
"""

class Main(BasePlugin):

    rows = 0  # 输入框的行数
    
    def handle(self, input):
        self.writehtml(BODY_HTML)


if __name__ == "__main__":
    # 命令行中执行
    pass

