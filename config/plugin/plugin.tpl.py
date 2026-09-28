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

from xnote.plugin import BasePluginV2
from xnote.webui import TextContainer

class Main(BasePluginV2):

    rows = 0  # 输入框的行数
    
    def handle(self, input):
        container = TextContainer()
        container.add_span("Hello, World")
        self.add_component(container)


if __name__ == "__main__":
    # 命令行中执行
    pass

