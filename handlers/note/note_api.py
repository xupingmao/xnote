# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/05 21:00:07
# @modified 2021/07/24 17:51:17
import xutils
import xauth
from xutils import dateutil
from . import dao

NOTE_DAO = xutils.DAO("note")


class GroupApiHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "0")
        list_type = xutils.get_argument("list_type", "")

        user_name = xauth.current_name()
        if list_type == "all":
            notes = self.list_all_group(user_name)
        else:
            notes = dao.list_by_parent(
                user_name, parent_id=id, offset=0, limit=1000, orderby="name")
        notes = list(filter(lambda x: x.type == "group", notes))

        parent_id = 0
        if id != "0":
            parent = NOTE_DAO.get_by_id(id)
            if parent != None:
                parent_id = parent.parent_id

        return dict(code="success", data=notes, parent_id=parent_id)
    
    def list_all_group(self, user_name):
        return dao.list_group(user_name)


def list_recent_groups(limit=5):
    creator = xauth.current_name()
    return NOTE_DAO.list_group(creator, orderby="mtime_desc", limit=5)


def list_recent_notes(limit=5):
    creator = xauth.current_name()
    return NOTE_DAO.list_recent_edit(creator, limit=limit)


def get_date_by_type(note, type):
    if type == "ddate":
        dtime = note.dtime
        if dtime is None:
            return note.mtime.split()[0]
        return dtime.split()[0]
    return note.ctime.split()[0]


def assemble_notes_by_date(notes, time_attr="ctime"):
    from collections import defaultdict
    notes_dict = defaultdict(list)
    for note in notes:
        if note.priority == 1:
            notes_dict["置顶"].append(note)
            continue
        if note.priority == 2:
            notes_dict["超级置顶"].append(note)
            continue
        datetime_str = note.get(time_attr)
        cdate = dateutil.format_date(datetime_str)
        notes_dict[cdate].append(note)
        note.badge_info = cdate

    result = []
    for date in notes_dict:
        item = (date, notes_dict[date])
        result.append(item)

    result.sort(key=lambda x: x[0], reverse=True)
    return result


xutils.register_func("page.list_recent_groups", list_recent_groups)
xutils.register_func("page.list_recent_notes", list_recent_notes)
xutils.register_func("note.get_date_by_type", get_date_by_type)
xutils.register_func("note.assemble_notes_by_date", assemble_notes_by_date)

xurls = (
    r"/note/api/group", GroupApiHandler
)
