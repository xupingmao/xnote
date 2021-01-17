# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/01/02 00:31:58
# @modified 2021/01/17 11:28:32

import xauth
import xtemplate
import xutils
import xconfig
from xutils import dateutil
from xtemplate import T

NOTE_DAO = xutils.DAO("note")
MSG_DAO  = xutils.DAO("message")


class NoteLink:
    def __init__(self, name, url, icon = "fa-cube", size = None, roles = None, category = "000"):
        self.type = "link"
        self.name = T(name)
        self.url  = url
        self.icon = icon
        self.size = size
        self.priority = 0
        self.ctime = ""
        self.hide  = False
        self.show_next  = True
        self.is_deleted = 0
        self.category = category

        # 角色
        if roles is None:
            roles = ("admin", "user")
        self.roles = roles

    def __str__(self):
        return str(self.__dict__)

class DictEntryLink(NoteLink):
    def __init__(self, size):
        NoteLink.__init__(self, "词典", "/note/dict",  "icon-dict", size = size)
        self.hide = xconfig.HIDE_DICT_ENTRY

def list_note_types(user_name = None):
    if user_name is None:
        user_name = xauth.current_name()

    note_stat = NOTE_DAO.get_note_stat(user_name)

    return [
        NoteLink("文档", "/note/document", "fa-file-text", size = note_stat.doc_count),
        NoteLink("相册", "/note/gallery", "fa-image", size = note_stat.gallery_count),
        NoteLink("清单", "/note/list", "fa-list", size = note_stat.list_count),
        NoteLink("表格", "/note/table", "fa-table", size = note_stat.table_count),
        NoteLink("日志", "/note/log", "fa-file-text", size = note_stat.log_count),
        DictEntryLink(size = note_stat.dict_count),
    ]

class NoteWorkspaceHandler:

    @xauth.login_required()
    def GET(self):
        recent_update_limit = 50
        if xtemplate.is_mobile_device():
            recent_update_limit = 10

        creator = xauth.current_name()
        memos   = [MSG_DAO.get_message_tag(creator, "task"), MSG_DAO.get_message_tag(creator, "log")]
        sticky_notes = NOTE_DAO.list_sticky(creator, limit = 5, orderby = "mtime_desc")
        hot_notes    = NOTE_DAO.list_hot(creator, limit = 5)
        note_groups  = NOTE_DAO.list_group(creator, orderby = "mtime_desc", limit = 5)
        recent_update_notes = NOTE_DAO.list_recent_edit(creator, limit = recent_update_limit, skip_deleted = True)

        return xtemplate.render_by_ua("note/page/note_workspace.html",
            html_title = T("笔记工作台"),
            hot_notes = hot_notes,
            memos = memos,
            note_groups = note_groups,
            recent_update_notes = recent_update_notes,
            sticky_notes = sticky_notes)


xutils.register_func("page.list_note_types", list_note_types)

xurls = (
    r"/note/workspace", NoteWorkspaceHandler
)