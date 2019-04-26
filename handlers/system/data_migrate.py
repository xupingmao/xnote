# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/04/27 02:09:28
# @modified 2019/04/27 02:23:19

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
from xutils import dbutil

HTML = """
<!-- Html -->

<div class="card">
    xnote从2.3版本开始，数据库采用leveldb，不再使用sqlite，此工具用于把sqlite数据库数据迁移到leveldb

    <div>
        <a class="btn" href="?action=db">迁移数据库</a>
    </div>

    <div class="top-offset-1">
        {{result}}
    </div>
</div>
"""

class MigrateHandler(BasePlugin):

    title = "数据迁移"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = None
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 0
        result = ""

        action = xutils.get_argument("action")
        if action == "db":
            result = migrate_db()
        self.writetemplate(HTML, result = result)

def migrate_db():
    migrate_note_history()
    return "数据库迁移完成!"


def migrate_note_history():
    db = xtables.get_note_history_table()
    for item in db.select():
        dbutil.put("note.history:%s:%s" % (item.note_id, item.version), item)

xurls = (
    "/system/data_migrate", MigrateHandler
)