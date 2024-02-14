# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/08/28 00:22:51
# @modified 2020/12/05 21:29:26

"""插件创建的工具，基于插件开发，但是其实已经不用了，实际创建插件的实现参考 fs/fs_add.py"""

import xutils
import os
import web
from xnote.core import xauth, xconfig
from xnote.core.xtemplate import BasePlugin
from xutils import History
from xutils import cacheutil
from xutils import Storage
from xutils import fsutil
from xutils import textutil, SearchResult, dateutil, dbutil, u
from . import dao as dao_visit_log


PLUGIN_API = xutils.Module("plugin")

DEFAULT_PLUGIN_TEMPLATE = '''# -*- coding:utf-8 -*-
# @since $since
# @author $author
# @plugin_id $plugin_id
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

    title = "PluginName"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network, develop}
    category = None
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 5
        self.writehtml(HTML)

    def on_init(self, context=None):
        # 插件初始化操作
        pass
'''

class NewPluginHandler(BasePlugin):
    """默认的插件声明入口，定义一个叫做Main的类"""

    def handle(self, input):
        self.description = '''请输入插件名称'''
        self.title = '通过模板创建插件'
        self.btn_text = '创建'
        self.rows = 1
        self.editable = False
        if input != '':
            name = os.path.join(xconfig.PLUGINS_DIR, input)
            if not name.endswith(".py"):
                name += ".py"
            if os.path.exists(name):
                return u("文件[%s]已经存在!") % u(name)
            user_name = xauth.current_name_str()
            code = xconfig.get_str("NEW_PLUGIN_TEMPLATE", DEFAULT_PLUGIN_TEMPLATE)
            code = code.replace("$since", xutils.format_datetime())
            code = code.replace("$author", user_name)
            code = code.replace("$plugin_id", xutils.create_uuid())
            xutils.writefile(name, code)
            # 添加一个访问记录，使得新增的插件排在前面
            basename = os.path.basename(name)
            dao_visit_log.add_visit_log(user_name, "/plugins/" + basename)
            raise web.seeother('/code/edit?path=%s' % name)


DEFAULT_COMMAND_TEMPLATE = '''# -*- coding:utf-8 -*-
# @since $since
# @author $author
import os
import xutils

def main(path = "", confirmed = False, **kw):
    # your code here
    pass
'''

class NewCommandPlugin(BasePlugin):
    """【不推荐】默认的插件声明入口，定义一个叫做Main的类
    已经不推荐使用命令扩展"""

    def handle(self, input):
        self.title = '通过模板创建命令扩展'
        self.description = '''请输入命令扩展名称'''
        self.btn_text = '创建'
        self.rows = 1
        self.editable = False
        if input != '':
            name = os.path.join(xconfig.COMMANDS_DIR, input)
            if not name.endswith(".py"):
                name += ".py"
            if os.path.exists(name):
                return u("文件[%s]已经存在!") % u(name)
            user_name = xauth.current_name_str()
            code = xconfig.get_str("NEW_COMMAND_TEMPLATE", DEFAULT_COMMAND_TEMPLATE)
            code = code.replace("$since", xutils.format_datetime())
            code = code.replace("$author", user_name)
            xutils.writefile(name, code)
            raise web.seeother('/code/edit?path=%s' % name)


xurls = (
    r"/plugins_new/command", NewCommandPlugin,
    r"/plugins_new", NewPluginHandler
)