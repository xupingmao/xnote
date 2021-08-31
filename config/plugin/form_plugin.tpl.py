# -*- coding:utf-8 -*-
# @api-level 2.8
# @since $since
# @author $author
# @version 1.0.0
# @category note
# @title 我的表单插件-$date
# @description 插件描述
# @icon-class fa-cube
# @require-admin true   # 仅对admin用户开放

import xconfig
import xutils
import xauth
import xmanager
import xtemplate
from xtemplate import BaseFormPlugin

HTML = """
<!-- Html -->
<div class="card">
    <p>Hello,World!</p>
</div>
"""

class Main(BaseFormPlugin):

    rows = 0

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

