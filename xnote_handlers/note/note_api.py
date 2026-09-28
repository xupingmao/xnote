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
from xnote.core import xtemplate
from xnote.core.xtemplate import T
from xutils import webutil
from xutils import textutil
from xnote_handlers.note import dao
from xnote_handlers.note.note_helper import assemble_notes_by_date
from xnote_handlers.note.note_service import NoteService
from xnote_handlers.note.note_edit import SaveAjaxHandler, RemoveAjaxHandler, update_and_notify

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


class NoteSearchApiHandler:

    @xauth.login_required()
    def GET(self):
        key = xutils.get_argument_str("key", "")
        limit = xutils.get_argument_int("limit", 20)
        user_name = xauth.current_name_str()
        user_id = xauth.current_user_id()
        words = textutil.split_words(key)

        result = []
        if len(words) == 0:
            return webutil.SuccessResult(data=result)

        for item in dao.search_name(words=words, creator=user_name, limit=limit):
            result.append(Storage(id=item.note_id, name=item.name,
                                  type="group" if item.is_group else "note",
                                  url=item.url))

        for item in dao.search_content(words=words, creator_id=user_id, limit=limit):
            result.append(Storage(id=item.id, name=item.name,
                                  type=item.type, url=item.url))
        return webutil.SuccessResult(data=result)


class NoteSaveApiHandler:

    @xauth.login_required()
    def POST(self):
        note_id = xutils.get_argument_str("id")
        content = xutils.get_argument_str("content", "")
        old = dao.get_by_id(note_id)
        if old is None:
            return webutil.FailedResult(code="404", message="笔记不存在")

        new_file = Storage(**old)
        new_file.content = content
        new_file.data = ""
        new_file.size = len(content)
        new_file.mtime = xutils.format_datetime()
        new_file.version = old.version + 1
        update_and_notify(old, new_file)
        return webutil.SuccessResult(data=old.get_url())


class NoteDeleteApiHandler:

    @xauth.login_required()
    def POST(self):
        return RemoveAjaxHandler().GET()


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
        NoteLink("评论", "/comment/mine", "fa-file-text", size = note_stat.comment_count),
        NoteLink("回收站", "/note/removed", "fa-trash", size = note_stat.removed_count),
    ]

def list_msg_types(user_name = None):
    if user_name is None:
        user_name = xauth.current_name_str()

    msg_stat  = msg_dao.get_message_stat(user_name)

    return [
        NoteLink("待办任务", "/todo/task", "fa-calendar-check-o", size = msg_stat.task_count),
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

class GroupSelectHtmlHandler:
    """移动笔记-选择笔记本的 HTML 片段，替代前端 art-template 渲染"""

    html = """
<div class="note-group-select col-md-12 scroll-y">
    {% if hasNoMatch %}
    <p class="align-center">没有匹配项,请重新输入关键字</p>
    {% end %}
    {% for group in groups %}
        {% if group.visible %}
        <h3 class="group-select-header">{{ group.title }}</h3>
        {% for item in group.children %}
        <p class="group-select-row">
            <i class="fa {{ item.icon }}"></i>
            <a class="link" data-id="{{ item.id }}">
                {{ item.path or item.name }}
            </a>
            <span class="group-select-size">{{ item.children_count }}</span>
        </p>
        {% end %}
        {% end %}
    {% end %}
</div>
"""

    @xauth.login_required()
    def GET(self):
        orderby = xutils.get_argument_str("orderby", "name")
        keyword = xutils.get_argument_str("keyword", "").lower()
        user_name = xauth.current_name_str()

        notes = dao.list_group_v2(user_name, limit=1000, orderby=orderby) + [dao.get_root()]
        if keyword != "":
            notes = [item for item in notes if keyword in (item.name or "").lower()]

        first = Storage(title="置顶", children=[])
        firstGroup = Storage(title="一级笔记本", children=[])
        second = Storage(title="其他笔记本", children=[])
        last = Storage(title="归档", children=[])

        for item in notes:
            if item.level >= 1:
                first.children.append(item)
            elif item.level < 0:
                last.children.append(item)
            elif item.parent_id == 0:
                firstGroup.children.append(item)
            else:
                second.children.append(item)

        groups = [first, firstGroup, second, last]
        for group in groups:
            group.visible = len(group.children) > 0

        hasNoMatch = len(notes) == 0
        return xtemplate.render_text(self.html, groups=groups, hasNoMatch=hasNoMatch)


class GroupTreeHtmlHandler:
    """笔记本树 HTML 片段，替代前端 art-template 渲染（递归构建整棵树）"""

    book_item_html = """
<div class="book-item {% if level > 0 %}child{% end %}">
    <div class="row">
        <i class="fa {{ item.icon }} fa-{{ item.icon }} black"></i>
        <a class="link2" href="{{ item.url }}">{{ item.name }}</a>
        <span class="tag lightgray">{{ childrenLength }}</span>
        {% if childrenBoxId > 0 %}
        <a class="op-link toggle-op" data-id="{{ childrenBoxId }}" data-state="close" onclick="toggleChildrenBox(this)">[展开]</a>
        {% end %}
        <span class="float-right">
            <a class="item-option" data-id="{{ item.id }}" data-name="{{ item.name }}" 
                onclick="xnote.note.renameByElement(this);" href="javascript:void(0);">重命名</a>
            <a class="item-option danger" data-id="{{ item.id }}" data-name="{{ item.name }}" data-post-action="refresh"
                onclick="xnote.note.deleteByElement(this)">删除</a>
            <input class="group-checkbox" type="checkbox" data-id="{{ item.id }}" data-name="{{ item.name }}"/>
        </span>
    </div>
</div>
"""

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        notes = dao.list_group_v2(user_name, limit=1000, orderby="name") + [dao.get_root()]

        note_map = {}
        for item in notes:
            item.children = []
            note_map[item.id] = item

        tree = []
        for item in notes:
            if item.id == 0:
                continue
            if item.parent_id == 0:
                tree.append(item)
            else:
                parent = note_map.get(item.parent_id)
                if parent:
                    parent.children.append(item)

        box_counter = [0]
        html = self.render_tree(tree, 0, box_counter)
        return html

    def render_tree(self, nodes, level, box_counter):
        parts = []
        for node in nodes:
            children = node.children
            children_box_id = 0
            if len(children) > 0:
                box_counter[0] += 1
                children_box_id = box_counter[0]
            # xtemplate.render_text 返回的是 bytes, 拼接前需要转成 str
            node_html = xtemplate.render_text(self.book_item_html,
                item=node, level=level, childrenBoxId=children_box_id, childrenLength=len(children))
            parts.append(node_html.decode("utf-8"))
            if len(children) > 0:
                child_html = self.render_tree(children, level + 1, box_counter)
                parts.append(f'<div class="children-box box-{children_box_id}">{child_html}</div>')
        return "".join(parts)


class MarkdownOutlineHandler:
    """编辑侧栏大纲 HTML 片段，替代前端 art-template 渲染（复制 editor.js MarkdownHeading 逻辑）"""

    html = """
{% for item in headings %}
<a class="list-item level-{{ item.level }}" data-line="{{ item.lineNo }}">
    <span>{{ item.name }}</span>
</a>
{% end %}
"""

    @xauth.login_required()
    def POST(self):
        text = xutils.get_argument_str("text", "")
        headings = self.parse_headings(text)
        return xtemplate.render_text(self.html, headings=headings)

    def parse_headings(self, text):
        lines = text.split("\n")
        headings = []
        line_no = 0
        is_in_code = False
        code_tag = "```"
        for line in lines:
            line_no += 1
            line = line.rstrip("\r")
            if is_in_code:
                if code_tag in line:
                    is_in_code = False
            else:
                if line and line[0] == "#":
                    level, name = self.parse_heading(line)
                    headings.append(Storage(level=level, lineNo=line_no, name=name))
                if code_tag in line:
                    is_in_code = True
        return headings

    def parse_heading(self, line):
        level = 0
        for c in line:
            if c == "#":
                level += 1
            elif c == " ":
                continue
            else:
                break
        return level, self.format_name(line)

    def format_name(self, text):
        start = 0
        end = len(text) - 1
        while start < len(text):
            c = text[start]
            if c in (" ", "\t", "#", "*"):
                start += 1
            else:
                break
        while end >= 0:
            c = text[end]
            if c in ("*", " ", "\t"):
                end -= 1
            else:
                break
        if end >= start:
            return text[start:end + 1]
        return text


xurls = (
    r"/api/v1/note/group", GroupApiHandler,
    r"/api/v1/note/group/select_html", GroupSelectHtmlHandler,
    r"/api/v1/note/group/tree_html", GroupTreeHtmlHandler,
    r"/note/api/markdown/outline", MarkdownOutlineHandler,
    r"/api/v1/note/stat", StatApiHandler,
    r"/api/v1/note/select_name", SelectNameHandler,
    r"/api/v1/note/content", NoteContentApiHandler,
    r"/api/v1/note/search", NoteSearchApiHandler,
    r"/api/v1/note/save", NoteSaveApiHandler,
    r"/api/v1/note/delete", NoteDeleteApiHandler,
)
