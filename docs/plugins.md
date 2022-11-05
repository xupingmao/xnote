# xnote插件

## 插件说明

插件统一在 `/${DATA}/scripts/plugins/` 目录下，可以自己创建子目录，一个Python文件代表一个插件，尽量保持插件功能的小巧。

插件需要定义一个Main类作为插件的入口，系统提供`xtemplate.BasePlugin`作为基类，可以参考后面的案例


## 新增插件

点击菜单的【插件】-> 【管理】 -> 选择【新建】下拉框 -> 【新建插件】

## 插件示例

```python
# -*- coding:utf-8 -*-
# @api-level 2.8
# @since 2020-09-12 20:11:15
# @author admin
# @category 文件
# @title 插件名称
# @description 插件描述
# @permitted-role admin  # 对admin用户开放
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

HTML = """
<!-- Html -->
<p>Hello,World!</p>
"""

class Main(BasePlugin):
    rows = 0 # 设置为0，不展示输入框

    def handle(self, input):
        self.writehtml(HTML)

```

## 插件卸载

直接删除对应的Python文件即可

## 插件的生命周期

一个插件在每次执行的时候都会产生新的实例，开发者可以把上下文信息放在插件对象的属性上面。

- 初始化：系统启动或者刷新的时候触发
- 响应客户请求：执行render方法
- 系统关闭：暂时无

