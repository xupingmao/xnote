# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/01/02 00:31:58
# @modified 2022/04/22 23:07:55

import xauth
import xtemplate
import xutils
import xconfig
from xtemplate import T
import handlers.note.dao as note_dao
import handlers.message.dao as msg_dao
import handlers.note.dao_book as book_dao
import handlers.note.dao_log as log_dao

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

    note_stat = note_dao.get_note_stat(user_name)

    return [
        NoteLink("标签", "/note/taglist", "fa-tags", size=note_stat.tag_count),
        NoteLink("文档", "/note/document", "fa-file-text", size = note_stat.doc_count),
        NoteLink("相册", "/note/gallery", "fa-image", size = note_stat.gallery_count),
        NoteLink("清单", "/note/list", "fa-list", size = note_stat.list_count),
        NoteLink("表格", "/note/table", "fa-table", size = note_stat.table_count),
        DictEntryLink(size = note_stat.dict_count),
        NoteLink("评论", "/note/comment/mine", "fa-file-text", size = note_stat.comment_count),
        NoteLink("回收站", "/note/removed", "fa-trash", size = note_stat.removed_count),
    ]

def list_msg_types(user_name = None):
    if user_name is None:
        user_name = xauth.current_name()

    msg_stat  = msg_dao.get_message_stat(user_name)

    return [
        NoteLink("待办任务", "/message/todo", "fa-calendar-check-o", size = msg_stat.task_count),
        NoteLink("随手记", "/message?tag=log", "fa-file-text-o", size = msg_stat.log_count),
    ]

def list_system_types(user_name = None):
    if user_name is None:
        user_name = xauth.current_name()

    msg_stat  = msg_dao.get_message_stat(user_name)

    return [
        NoteLink("插件", "/plugins_list", "fa-th-large", size = msg_stat.task_count),
        NoteLink("设置", "/system/settings", "fa-gear", size = ""),
    ]

def list_special_groups(user_name = None):
    if user_name is None:
        user_name = xauth.current_name()

    # 短消息：任务、通知和备忘
    fixed_books = []
    fixed_books.append(msg_dao.get_message_tag(user_name, "task"))
    fixed_books.append(msg_dao.get_message_tag(user_name, "log"))
    fixed_books.append(NoteLink("智能笔记本", "/note/group_list?tab=smart&show_back=true", 
        size = book_dao.SmartGroupService.count_smart_group(), 
        icon = "fa-folder"))

    return fixed_books

class NoteWorkspaceHandler:

    @xauth.login_required()
    def GET(self):
        recent_update_limit = 50
        if xtemplate.is_mobile_device():
            recent_update_limit = 10

        creator = xauth.current_name()
        memos = [msg_dao.get_message_tag(creator, "task"), msg_dao.get_message_tag(creator, "log")]
        sticky_notes = note_dao.list_sticky(creator, limit = 5, orderby = "mtime_desc")
        hot_notes    = log_dao.list_hot(creator, limit = 5)
        note_groups  = note_dao.list_group(creator, orderby = "mtime_desc", limit = 5)
        recent_update_notes = log_dao.list_recent_edit(creator, limit = recent_update_limit, skip_deleted = True)

        return xtemplate.render_by_ua("note/page/index/note_workspace.html",
            html_title = T("笔记工作台"),
            hot_notes = hot_notes,
            memos = memos,
            note_groups = note_groups,
            recent_update_notes = recent_update_notes,
            sticky_notes = sticky_notes)


xutils.register_func("page.list_note_types", list_note_types)
xutils.register_func("page.list_msg_types", list_msg_types)
xutils.register_func("page.list_system_types", list_system_types)
xutils.register_func("page.list_special_groups", list_special_groups)
xutils.register_func("url:/note/workspace", NoteWorkspaceHandler)

xurls = (
    r"/note/workspace", NoteWorkspaceHandler
)