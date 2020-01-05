# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/05 21:00:07
# @modified 2020/01/05 21:31:58
import xutils
import xauth

NOTE_DAO = xutils.DAO("note")

class GroupApiHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", 0, type = int)
        user_name = xauth.current_name()

        notes = NOTE_DAO.list_by_parent(user_name, parent_id = id, offset = 0, limit = 1000)
        notes = list(filter(lambda x: x.type == "group", notes))

        parent_id = 0
        if id != 0:
            parent = NOTE_DAO.get_by_id(id)
            if parent != None:
                parent_id = parent.parent_id

        return dict(code = "success", data = notes, parent_id = parent_id)

xurls = (
    r"/note/api/group", GroupApiHandler
)