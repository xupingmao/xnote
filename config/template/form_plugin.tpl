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
import xtemplate
from xtemplate import BaseFormPlugin

HTML = """
<!-- Html -->
<p>Hello,World!</p>
"""

class Main(BaseFormPlugin):

    title    = "Hello_World_Form"
    category = "form"

    def get_input_template(self):
        return "Input Template"

    def handle_input(self, input):
        pass
    
    def handle(self, input):
        if input != "":
            self.handle_input(self, input)

        # load data list
        self.writehtml(HTML)


if __name__ == "__main__":
    # 命令行中执行
    pass

