# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/05 21:00:07
# @modified 2021/07/24 17:51:17
import xutils
import xnote_handlers.note.dao_log as dao_log
import xnote_handlers.message.dao as msg_dao
import xnote_handlers.note.dao_book as book_dao

from typing import List
from xutils import Storage
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core.xtemplate import T
from xutils import webutil
from xutils import textutil
from xnote_handlers.note import dao
from xnote_handlers.note.note_helper import assemble_notes_by_date
from xnote_handlers.note.note_service import NoteService

NOTE_DAO = xutils.DAO("note")


class GroupApiHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id", 0)
        list_type = xutils.get_argument_str("list_type", "")
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

        result = webutil.SuccessResult(data=notes)
        result.parent_id = parent_id
        return result
    
    def list_all_group(self, user_name, orderby=""):
        result = dao.list_group_v2(user_name, limit=1000, orderby=orderby)
        root = dao.get_root()
        return [root] + result


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

class NoteContentApiHandler:

    @xauth.login_required()
    def GET(self):
        note_id = xutils.get_argument_int("id")
        note = dao.get_by_id(note_id)
        if note is None:
            return webutil.FailedResult(code="404", message="笔记不存在")
        user_id = xauth.current_user_id()
        NoteService.check_auth(note, user_id)
        return webutil.SuccessResult(data=note.content)


class Select2ResultItem(dict):
    def __init__(self, id=0, text=""):
        self["id"] = id
        self["text"] = text

class Select2Result(Storage):
    def __init__(self, results: List[Select2ResultItem]=[]):
        self.results = results


class SelectNameHandler:

    @xauth.login_required()
    def GET(self):
        name = xutils.get_argument_str("search")
        show_type = xutils.get_argument_bool("show_type", True)
        words = textutil.split_words(name)
        creator = xauth.current_name_str()
        results:List[Select2ResultItem] = []

        for note_index in dao.search_name(words=words, creator=creator, limit=100):
            text = note_index.name
            if show_type:
                if note_index.is_group:
                    text = "[笔记本]" + text
                if note_index.is_alias:
                    text = "[别名]" + text
            results.append(Select2ResultItem(id=note_index.note_id, text=text))

        return Select2Result(results=results)

xutils.register_func("page.list_recent_groups", list_recent_groups)
xutils.register_func("page.list_recent_notes", list_recent_notes)
xutils.register_func("note.get_date_by_type", get_date_by_type)
xutils.register_func("note.assemble_notes_by_date", assemble_notes_by_date)


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

    note_stat = dao.get_note_stat(user_name)

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
        user_name = xauth.current_name_str()

    msg_stat  = msg_dao.get_message_stat(user_name)

    return [
        NoteLink("待办任务", "/message/todo", "fa-calendar-check-o", size = msg_stat.task_count),
        NoteLink("随手记", "/message?tag=log", "fa-file-text-o", size = msg_stat.log_count),
    ]

def list_system_types(user_name = None):
    if user_name is None:
        user_name = xauth.current_name_str()

    msg_stat  = msg_dao.get_message_stat(user_name)

    return [
        NoteLink("插件", "/plugin_list", "fa-th-large", size = msg_stat.task_count),
        NoteLink("设置", "/system/settings", "fa-gear", size = ""),
    ]

def list_special_groups(user_name = None):
    if user_name is None:
        user_name = xauth.current_name()

    fixed_books = []
    fixed_books.append(msg_dao.get_message_stat_item(user_name, "task"))
    fixed_books.append(msg_dao.get_message_stat_item(user_name, "log"))
    fixed_books.append(NoteLink("智能笔记本", "/note/group_list?tab=smart&show_back=true", 
        size = book_dao.SmartGroupService.count_smart_group(), 
        icon = "fa-folder"))

    return fixed_books


xutils.register_func("page.list_note_types", list_note_types)
xutils.register_func("page.list_msg_types", list_msg_types)
xutils.register_func("page.list_system_types", list_system_types)
xutils.register_func("page.list_special_groups", list_special_groups)

xurls = (
    r"/note/api/group", GroupApiHandler,
    r"/note/api/stat", StatApiHandler,
    r"/note/api/select_name", SelectNameHandler,
    r"/note/api/content", NoteContentApiHandler,
)
