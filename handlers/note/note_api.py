# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/05 21:00:07
# @modified 2021/01/05 00:20:59
import xutils
import xauth

NOTE_DAO = xutils.DAO("note")

class GroupApiHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", 0, type = int)
        user_name = xauth.current_name()

        notes = NOTE_DAO.list_by_parent(user_name, parent_id = id, offset = 0, limit = 1000, orderby = "name")
        notes = list(filter(lambda x: x.type == "group", notes))

        parent_id = 0
        if id != 0:
            parent = NOTE_DAO.get_by_id(id)
            if parent != None:
                parent_id = parent.parent_id

        return dict(code = "success", data = notes, parent_id = parent_id)

def list_recent_groups(limit = 5):
    creator = xauth.current_name()
    return NOTE_DAO.list_group(creator, orderby = "mtime_desc", limit = 5)

def list_recent_notes(limit = 5):
    creator = xauth.current_name()
    return NOTE_DAO.list_recent_edit(creator, limit = limit)

xutils.register_func("page.list_recent_groups", list_recent_groups)
xutils.register_func("page.list_recent_notes", list_recent_notes)

xurls = (
    r"/note/api/group", GroupApiHandler
)