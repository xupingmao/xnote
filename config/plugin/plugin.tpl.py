# -*- coding:utf-8 -*-
# @id $plugin_id
# @api-level 2.8
# @since $since
# @author $author
# @version 1.0.0
# @category note
# @title 我的插件-$date
# @description 插件描述
# @permitted-role admin  # 对admin用户开放
# @tag system
# @tag test
# @enabled
# @debug  # 开启调试
# @icon-class fa-cube

import os
import re
import math
import time
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

