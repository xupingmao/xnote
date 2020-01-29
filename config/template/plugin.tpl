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

HTML = """
<!-- Html -->
"""

class Main(BasePlugin):
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 5
        self.writehtml(HTML)


if __name__ == "__main__":
    # 命令行中执行
    pass

