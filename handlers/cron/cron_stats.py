# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/07/05 17:35:53
# @modified 2022/04/16 08:54:27
from __future__ import print_function

import xauth
from xutils import dateutil
from handlers.note import dao as note_dao

def print_debug_info(*args):
    new_args = [dateutil.format_time(), "[stats]"]
    new_args += args
    print(*new_args)

"""统计数据更新的定时任务"""

# 衰减单位
DECREMENT = 1

def update_note_index_by_notes(notes):
    for note in notes:
        old_index = note.hot_index or 0
        # 按照线性关系衰退
        new_index = max(old_index - DECREMENT, 0)
        if new_index != old_index:
            print("update hot_index, note_id=%s, old=%s, new=%s" % (note.id, old_index, new_index))
            note.hot_index = new_index
            note_dao.update_index(note)

class StatsHandler:

    @xauth.login_required("admin")
    def GET(self):
        return u"功能暂时停用"

xurls = (
    r"/cron/stats", StatsHandler
)