# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/07/05 17:35:53
# @modified 2021/12/25 22:37:40
import xutils
import xauth
from xutils import dbutil
from xutils import dateutil


def print_debug_info(*args):
    new_args = [dateutil.format_time(), "[stats]"]
    new_args += args
    print(*new_args)

"""统计数据更新的定时任务"""
NOTE_DAO = xutils.DAO("note")

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
            NOTE_DAO.update_index(note)

def update_public_index():
    # TODO: 加快切换速度
    # 方案1: 使用两个index表进行切换
    table = dbutil.get_hash_table("note_public_hot_index")
    for key in table.iter():
        table.delete(key)

    note_table = dbutil.get_hash_table("note_index")
    for key, note in note_table.iter(offset = 0, limit = -1):
        print_debug_info("public_index", key, note)

        if note.is_deleted:
            continue
        if note.is_public:
            key = "%010d_%s" % (note.hot_index, note.id)
            table.put(key, note.id)
            print_debug_info("public_index", note.id)


class StatsHandler:

    @xauth.login_required("admin")
    def GET(self):
        update_public_index()
        return u"功能暂时停用"

        user_names = xauth.list_user_names()
        for user_name in user_names:
            notes = NOTE_DAO.list_hot(user_name, 0, -1)
            update_note_index_by_notes(notes)
        return dict(code = "success")

xurls = (
    r"/cron/stats", StatsHandler
)