# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/05 21:00:07
# @modified 2021/07/24 17:51:17
import xutils
from xnote.core import xauth
from handlers.note import dao
import handlers.note.dao_log as dao_log
from handlers.note.note_helper import assemble_notes_by_date

NOTE_DAO = xutils.DAO("note")


class GroupApiHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id", 0)
        list_type = xutils.get_argument("list_type", "")
        orderby = xutils.get_argument_str("orderby", "mtime_desc")

        user_name = xauth.current_name_str()
        if list_type == "all":
            notes = self.list_all_group(user_name, orderby=orderby)
        else:
            notes = dao.list_by_parent(
                user_name, parent_id=id, offset=0, limit=1000, orderby="name")
        notes = list(filter(lambda x: x.type == "group", notes))

        parent_id = 0
        if id != 0:
            parent = dao.get_by_id(id)
            if parent != None:
                parent_id = parent.parent_id

        return dict(code="success", data=notes, parent_id=parent_id)
    
    def list_all_group(self, user_name, orderby=""):
        return dao.list_group_v2(user_name, limit=1000, orderby=orderby)


def list_recent_groups(limit=5):
    creator = xauth.current_name()
    return dao.list_group(creator, orderby="mtime_desc", limit=5)


def list_recent_notes(limit=5):
    creator = xauth.current_name()
    return dao_log.list_recent_edit(creator, limit=limit)


def get_date_by_type(note, type):
    if type == "ddate":
        dtime = note.dtime
        if dtime is None:
            return note.mtime.split()[0]
        return dtime.split()[0]
    return note.ctime.split()[0]

class StatApiHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        return dict(code="success", data=dao.get_note_stat(user_name=user_name))


xutils.register_func("page.list_recent_groups", list_recent_groups)
xutils.register_func("page.list_recent_notes", list_recent_notes)
xutils.register_func("note.get_date_by_type", get_date_by_type)
xutils.register_func("note.assemble_notes_by_date", assemble_notes_by_date)

xurls = (
    r"/note/api/group", GroupApiHandler,
    r"/note/api/stat", StatApiHandler,
)
