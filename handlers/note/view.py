# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12
# @modified 2019/10/26 23:47:01
import profile
import math
import re
import web
import xauth
import xutils
import xconfig
import xtables
import xtemplate
import xmanager
import os
from web import HTTPError
from xconfig import Storage
from xutils import History
from xutils import dbutil
from xutils import fsutil

PAGE_SIZE = xconfig.PAGE_SIZE
NOTE_DAO = xutils.DAO("note")

@xmanager.listen("note.view", is_async=True)
def visit_by_id(ctx):
    id = ctx.id
    xutils.call("note.visit", id)

def render_note_list(notes, file):
    return xtemplate.render("note/note_list_left.html", 
        notes = notes, 
        files = notes,
        file  = file,
        show_search = False)

def handle_left_dir(kw, user_name, file, op):
    is_iframe = xutils.get_argument("is_iframe")
    dir_type = xutils.get_argument("dir_type")
    tags = xutils.get_argument("tags")

    if file.type in ("html", "csv"):
        kw.show_aside = False

    if file.type == "group":
        return
    if is_iframe == "true":
        return

    parent_id      = file.parent_id
    kw.show_left   = True
    kw.show_groups = True
    kw.dir_type    = dir_type

    if op == "edit":
        kw.show_search = False

    if tags != "" and tags != None:
        kw.groups = NOTE_DAO.list_by_tag(user_name, tags)
    elif dir_type == "sticky":
        kw.groups = NOTE_DAO.list_sticky(user_name)
    elif dir_type == "public":
        kw.groups = NOTE_DAO.list_public(0, xconfig.PAGE_SIZE)
    elif dir_type == "recent_edit":
        kw.groups = NOTE_DAO.list_recent_edit(user_name, 0, 200)
    elif dir_type == "recent_created":
        kw.groups = NOTE_DAO.list_recent_created(user_name, 0, 200)
    else:
        parent = NOTE_DAO.get_by_id(parent_id)
        if parent is None:
            return
        kw.groups = NOTE_DAO.list_by_parent(user_name, parent_id, 0, 200, parent.orderby)

def handle_note_recommend(kw, file, user_name):
    ctx = Storage(id=file.id, name = file.name, creator = file.creator, 
        content = file.content,
        parent_id = file.parent_id,
        result = [])
    xmanager.fire("note.recommend", ctx)
    kw.recommended_notes = ctx.result
    kw.next_note = NOTE_DAO.find_next_note(file, user_name)
    kw.prev_note = NOTE_DAO.find_prev_note(file, user_name)

def handle_note_content(file):
    content = file.content
    content = content.replace(u'\xad', '\n')
    content = content.replace(u'\n', '<br/>')
    file.data = file.data.replace(u"\xad", "\n")
    file.data = file.data.replace(u'\n', '<br/>')
    if file.data == None or file.data == "":
        file.data = content

def handle_note_files(kw, file):
    fpath = os.path.join(xconfig.UPLOAD_DIR, file.creator, str(file.parent_id), str(file.id))
    filelist = []
    # 处理相册
    if file.type == "gallery":
        if os.path.exists(fpath):
            filelist = fsutil.list_files(fpath, webpath = True)
        file.path = fpath

    kw.path = fpath
    kw.filelist = filelist

class ViewHandler:

    xconfig.note_history = History("笔记浏览记录", 200)

    @xutils.timeit(name = "Note.View", logfile = True)
    def GET(self, op, id = None):
        if id is None:
            id = xutils.get_argument("id", "")
        name          = xutils.get_argument("name", "")
        page          = xutils.get_argument("page", 1, type=int)
        pagesize      = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        show_menu     = xutils.get_argument("show_menu", "true") != "false"
        show_search   = xutils.get_argument("show_search", "true") != "false"
        orderby       = xutils.get_argument("orderby", None)
        is_iframe     = xutils.get_argument("is_iframe", "false")
        user_name     = xauth.current_name()
        show_add_file = False
        title         = None
        show_pagination = True
        show_search_div = False

        kw = Storage()
        kw.show_left = False
        kw.show_groups = False
        kw.groups = []
        kw.recommended_notes = []

        if id == "0":
            raise web.found("/")
        # 回收站的笔记也能看到
        if id == "" and name == "":
            raise HTTPError(504)
        if id != "":
            file = NOTE_DAO.get_by_id(id)
        elif name is not None:
            file = NOTE_DAO.get_by_name(name)
        if file is None:
            raise web.notfound()
        
        if file.type != "group" and not file.is_public and user_name != "admin" and user_name != file.creator:
            raise web.seeother("/unauthorized")
        pathlist        = xutils.call("note.list_path", file)
        can_edit        = (file.creator == user_name) or (user_name == "admin")
        role            = xauth.get_current_role()

        # 定义一些变量
        show_mdate     = False
        files          = []
        recent_created = []
        amount         = 0
        show_recommend = False
        template_name  = "note/view.html"
        next_note      = None
        prev_note      = None

        xconfig.note_history.put(dict(user=user_name, 
            link = "/note/%s" % id, name = file.name))

        title  = file.name
        if file.type == "group":
            if orderby != None and file.orderby != orderby:
                NOTE_DAO.update(where = dict(id = file.id, creator = file.creator), orderby = orderby)
            else:
                orderby = file.orderby

            files  = xutils.call("note.list_by_parent", user_name, file.id, (page-1)*pagesize, pagesize, orderby)
            amount = xutils.call("note.count", user_name, file.id)
            content         = file.content
            show_search_div = True
            show_add_file   = True
            show_mdate      = True
            # return render_note_list(files, file)
        elif file.type == "md" or file.type == "text":
            content = file.content
            show_recommend = True
            show_pagination = False
            if op == "edit":
                show_recommend = False
                template_name = "note/editor/markdown_edit.html"
        else:
            # post/html 等其他类型
            handle_note_content(file)
            show_recommend = True
            show_pagination = False

        # 处理笔记背后的文件系统
        handle_note_files(kw, file)

        if show_recommend and user_name is not None:
            # 推荐系统
            handle_note_recommend(kw, file, user_name)
            
        
        xmanager.fire("note.view", file)
        show_aside = True
        if op == "edit":
            show_aside = False

        if is_iframe == "true":
            show_menu = False
            show_search = False

        kw.show_aside = show_aside
        kw.show_menu  = show_menu
        kw.show_search = show_search

        # 如果是页面，需要查出上级目录列表
        handle_left_dir(kw, user_name, file, op)

        return xtemplate.render(template_name,
            html_title    = title,
            file          = file, 
            note_id       = id,
            op            = op,
            show_mdate    = show_mdate,
            show_add_file = show_add_file,
            show_pagination = show_pagination,
            can_edit = can_edit,
            pathlist = pathlist,
            page_max = math.ceil(amount/pagesize),
            page     = page,
            page_url = "/note/view?id=%s&orderby=%s&page=" % (id, orderby),
            files    = files, 
            recent_created    = recent_created,
            is_iframe         = is_iframe, **kw)

class ViewByIdHandler(ViewHandler):

    def GET(self, id):
        return super(ViewByIdHandler, self).GET("view", id)

    def POST(self, id):
        return super(ViewByIdHandler, self).POST("view", id)

class PrintHandler:

    @xauth.login_required()
    def GET(self):
        id        = xutils.get_argument("id")
        file      = xutils.call("note.get_by_id", id)
        user_name = xauth.current_name()
        if file.is_public != 1 and user_name != "admin" and user_name != file.creator:
            raise web.seeother("/unauthorized")
        return xtemplate.render("note/tools/print.html", show_menu = False, note = file)

def sqlite_escape(text):
    if text is None:
        return "NULL"
    if not (isinstance(text, str)):
        return repr(text)
    text = text.replace("'", "''")
    return "'" + text + "'"

def result(success = True, msg=None):
    return {"success": success, "result": None, "msg": msg}

def get_link(filename, webpath):
    if xutils.is_img_file(filename):
        return "![%s](%s)" % (filename, webpath)
    return "[%s](%s)" % (filename, webpath)


class Upvote:

    @xauth.login_required()
    def GET(self, id):
        id = int(id)
        db = xtables.get_file_table()
        file = db.select_first(where=dict(id=int(id)))
        db.update(priority=1, where=dict(id=id))
        raise web.seeother("/note/view?id=%s" % id)

class Downvote:

    @xauth.login_required()
    def GET(self, id):
        id = int(id)
        db = xtables.get_file_table()
        file = db.select_first(where=dict(id=int(id)))
        db.update(priority=0, where=dict(id=id))
        raise web.seeother("/note/view?id=%s" % id)

class MarkHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        db = xtables.get_file_table()
        db.update(is_marked=1, where=dict(id=id))
        raise web.seeother("/note/view?id=%s"%id)

class UnmarkHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        db = xtables.get_file_table()
        db.update(is_marked=0, where=dict(id=id))
        raise web.seeother("/note/view?id=%s"%id)

class DictHandler:

    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_dict_table()
        items = db.select(order="id", limit=PAGE_SIZE, offset=(page-1)*PAGE_SIZE)
        def convert(item):
            v = Storage()
            v.name = item.key
            v.summary = item.value
            v.mtime = item.mtime
            v.ctime = item.ctime
            v.url = "#"
            v.priority = 0
            return v
        items = map(convert, items)
        count = db.count()
        page_max = math.ceil(count / PAGE_SIZE)

        return xtemplate.render("note/view.html", 
            show_aside = True,
            files = list(items), 
            file_type = "group",
            show_opts = False,
            page = page,
            page_max = page_max,
            page_url = "/note/dict?page=")

class NoteHistoryHandler:

    @xauth.login_required()
    def GET(self):
        note_id = xutils.get_argument("id")
        creator = xauth.current_name()
        note = NOTE_DAO.get_by_id_creator(note_id, creator)
        if note is None:
            history_list = []
        else:
            history_list = NOTE_DAO.list_history(note_id)
        return xtemplate.render("note/template/history_list.html", 
            current_note = note,
            history_list = history_list,
            show_aside = True)

class HistoryViewHandler:

    @xauth.login_required()
    def GET(self):
        note_id = xutils.get_argument("id")
        version = xutils.get_argument("version")
        
        creator = xauth.current_name()
        note = xutils.call("note.get_by_id_creator", note_id, creator)
        content = ""
        if note != None:
            note = xutils.call("note.get_history", note_id, version)
            if note != None:
                content = note.content
        return dict(code = "success", data = content)


class NoticeHandler:

    @xauth.login_required()
    def GET(self):
        return xtemplate.render("note/notice.html")

class QueryHandler:

    @xauth.login_required("admin")
    def GET(self, action = ""):
        if action == "get_by_id":
            id = xutils.get_argument("id")
            return dict(code = "success", data = NOTE_DAO.get_by_id(id))
        if action == "get_by_name":
            name = xutils.get_argument("name")
            return dict(code = "success", data = NOTE_DAO.get_by_name(name))
        return dict(code="fail", message = "unknown action")

xurls = (
    r"/note/(edit|view)"   , ViewHandler,
    r"/note/print"         , PrintHandler,
    r"/note/(\d+)"         , ViewByIdHandler,
    r"/note/dict"          , DictHandler,
    r"/note/history"       , NoteHistoryHandler,
    r"/note/history_view"  , HistoryViewHandler,
    r"/note/notice"        , NoticeHandler,
    r"/note/query/(\w+)"   , QueryHandler,
    
    r"/file/(\d+)/upvote"  , Upvote,
    r"/file/(\d+)/downvote", Downvote,
    r"/file/mark"          , MarkHandler,
    r"/file/unmark"        , UnmarkHandler,
    r"/file/markdown"      , ViewHandler
)

