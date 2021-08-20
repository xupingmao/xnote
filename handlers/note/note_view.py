# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12
# @modified 2021/08/20 23:30:39
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
from xtemplate import T
from .constant import CREATE_BTN_TEXT_DICT

PAGE_SIZE = xconfig.PAGE_SIZE
NOTE_DAO = xutils.DAO("note")

@xmanager.listen("note.view")
def visit_by_id(ctx):
    note_id   = ctx.id
    user_name = ctx.user_name
    NOTE_DAO.visit(user_name, note_id)

def check_auth(file, user_name):
    if user_name == "admin":
        return

    if user_name == file.creator:
        return

    if file.is_public == 1:
        return

    # 笔记的分享
    if NOTE_DAO.get_share_to(user_name, file.id) != None:
        return

    # 笔记本的分享
    if NOTE_DAO.get_share_to(user_name, file.parent_id) != None:
        return
    
    raise web.seeother("/unauthorized")

def handle_left_dir(kw, user_name, file, op):
    is_iframe = xutils.get_argument("is_iframe")
    dir_type = xutils.get_argument("dir_type")
    tags = xutils.get_argument("tags")

    if file.type in ("html", "csv"):
        kw.show_aside = False

def handle_note_recommend(kw, file, user_name):
    ctx = Storage(id=file.id, name = file.name, creator = file.creator, 
        content = file.content,
        parent_id = file.parent_id,
        result = [])
    xmanager.fire("note.recommend", ctx)
    kw.recommended_notes = ctx.result
    kw.next_note = NOTE_DAO.find_next_note(file, user_name)
    kw.prev_note = NOTE_DAO.find_prev_note(file, user_name)

def view_gallery_func(file, kw):
    fpath = os.path.join(xconfig.UPLOAD_DIR, file.creator, str(file.parent_id), str(file.id))
    filelist = []
    # 处理相册
    # print(file)
    fpath = NOTE_DAO.get_gallery_path(file)
    # print(fpath)
    if fpath != None:
        filelist = fsutil.list_files(fpath, webpath = True)
    file.path     = fpath
    kw.show_aside = False
    kw.path       = fpath
    kw.filelist   = filelist

def view_html_func(file, kw):
    """处理html/post等类型的文档"""
    content = file.content
    content = content.replace(u'\xad', '\n')
    content = content.replace(u'\n', '<br/>')
    file.data = file.data.replace(u"\xad", "\n")
    file.data = file.data.replace(u'\n', '<br/>')
    if file.data == None or file.data == "":
        file.data = content
    kw.show_recommend = True
    kw.show_pagination = False

def view_md_func(file, kw):
    kw.content = file.content
    kw.show_recommend = True
    kw.show_pagination = False
    if kw.op == "edit":
        kw.show_recommend = False
        kw.template_name = "note/editor/markdown_edit.html"

def view_group_timeline_func(note, kw):
    raise web.found("/note/timeline?type=default&parent_id=%s" % note.id)

def view_group_list_func(file, kw):
    # 代码暂时不用
    orderby   = kw.orderby
    user_name = kw.user_name
    page      = kw.page
    # pagesize  = kw.pagesize
    pagesize  = 1000

    if kw.op == "edit":
        # 编辑笔记本的简介
        kw.show_recommend = False
        kw.template_name = "note/editor/markdown_edit.html"
        return

    if orderby != None and orderby != "" and file.orderby != orderby:
        NOTE_DAO.update(file.id, orderby = orderby)
    else:
        orderby = file.orderby

    if orderby not in ("ctime_priority", "name"):
        orderby = "ctime_priority"

    files  = NOTE_DAO.list_by_parent(file.creator, file.id, (page-1)*pagesize, pagesize, orderby)
    amount             = file.size
    kw.content         = file.content
    kw.show_search_div = True
    kw.show_add_file   = True
    kw.show_aside      = False
    kw.show_pagination = True
    kw.files           = files
    kw.show_parent_link = False
    kw.page_max        = math.ceil(amount/pagesize)
    kw.show_cdate = True
    kw.parent_id  = file.id
    kw.template_name = "note/page/detail/group_detail.html"

    share_from_info = NOTE_DAO.get_share_from(user_name, file.id)
    if share_from_info != None:
        kw.share_to_list = share_from_info.share_to_list
    else:
        kw.share_to_list = []

def view_list_func(note, kw):
    kw.show_aside = False
    kw.show_pagination = False
    kw.show_comment_title = True
    kw.comment_title = T("清单项")

def view_table_func(note, kw):
    kw.show_aside = False

VIEW_FUNC_DICT = {
    "group": view_group_list_func,
    "md"  : view_md_func,
    "text": view_md_func,
    "memo": view_md_func,
    "log" : view_md_func,
    "list": view_list_func,
    "csv" : view_table_func,
    "gallery": view_gallery_func,
    "html": view_html_func,
    "post": view_html_func,
}

def find_note_for_view0(token, id, name):
    if token != "":
        return NOTE_DAO.get_by_token(token)
    if id != "":
        return NOTE_DAO.get_by_id(id)
    if name != "":
        return NOTE_DAO.get_by_name(xauth.current_name(), name)

    raise HTTPError(504)

def find_note_for_view(token, id, name):
    note = find_note_for_view0(token, id, name)
    if note != None:
        note.mdate = note.mtime.split(" ")[0]
        note.cdate = note.ctime.split(" ")[0]
        note.adate = note.atime.split(" ")[0]
    return note

def create_view_kw():
    kw = Storage()
    kw.show_left   = False
    kw.show_groups = False
    kw.show_aside  = True
    kw.groups      = []
    kw.files       = []
    kw.show_mdate  = False
    kw.recommended_notes = []
    kw.show_add_file     = False
    kw.template_name     = "note/page/view.html"
    kw.search_type       = "note"
    kw.comment_source_class = "hide"

    return kw

class ViewHandler:

    @xutils.timeit(name = "Note.View", logfile = True)
    def GET(self, op, id = None):
        if id is None:
            id = xutils.get_argument("id", "")
        name          = xutils.get_argument("name", "")
        page          = xutils.get_argument("page", 1, type=int)
        pagesize      = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        show_menu     = xutils.get_argument("show_menu", "true") != "false"
        show_search   = xutils.get_argument("show_search", "true") != "false"
        orderby       = xutils.get_argument("orderby", "")
        is_iframe     = xutils.get_argument("is_iframe", "false")
        token         = xutils.get_argument("token", "")
        user_name     = xauth.current_name()
        skey          = xutils.get_argument("skey")

        kw = create_view_kw()

        kw.op          = op
        kw.user_name   = user_name
        kw.page        = page
        kw.orderby     = orderby
        kw.pagesize    = pagesize
        kw.page_url    = "/note/view?id=%s&orderby=%s&page=" % (id, orderby)

        # print("skey:", skey)

        if id == "0":
            raise web.found("/")

        if skey != None and skey != "":
            try:
                file = NOTE_DAO.get_or_create(skey, user_name)
            except Exception as e:
                return xtemplate.render("error.html", error = e)
        else:
            # 回收站的笔记也能看到
            file = find_note_for_view(token, id, name)

        if file is None:
            raise web.notfound()

        if token == "":
            check_auth(file, user_name)

        pathlist        = NOTE_DAO.list_path(file)
        can_edit        = (file.creator == user_name) or (user_name == "admin")
        role            = xauth.get_current_role()

        # 定义一些变量
        recent_created = []
        show_recommend = False
        next_note      = None
        prev_note      = None

        event_ctx = Storage(id = file.id, user_name = user_name)
        xmanager.fire("note.view", event_ctx)

        view_func = VIEW_FUNC_DICT.get(file.type, view_md_func)
        view_func(file, kw)

        if show_recommend and user_name is not None:
            # 推荐系统
            handle_note_recommend(kw, file, user_name)
        
        if op == "edit":
            kw.show_aside = False
            kw.show_search = False
            kw.show_comment = False

        if is_iframe == "true":
            kw.show_menu = False
            kw.show_search = False

        template_name = kw['template_name']
        del kw['template_name']

        # 如果是页面，需要查出上级目录列表
        handle_left_dir(kw, user_name, file, op)
        return xtemplate.render_by_ua(template_name,
            html_title    = file.name,
            file          = file, 
            note_id       = id,
            can_edit = can_edit,
            pathlist = pathlist,
            recent_created    = recent_created,
            CREATE_BTN_TEXT_DICT = CREATE_BTN_TEXT_DICT,
            is_iframe         = is_iframe, **kw)

class ViewByIdHandler(ViewHandler):

    def GET(self, id):
        return ViewHandler.GET(self, "view", id)

    def POST(self, id):
        return ViewHandler.POST(self, "view", id)

class PrintHandler:

    @xauth.login_required()
    def GET(self):
        id        = xutils.get_argument("id")
        file      = xutils.call("note.get_by_id", id)
        user_name = xauth.current_name()
        check_auth(file, user_name)
        return xtemplate.render("note/page/print.html", show_menu = False, note = file)

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
        return xtemplate.render("note/page/history_list.html", 
            current_note = note,
            history_list = history_list,
            show_aside = True)

class HistoryViewHandler:

    @xauth.login_required()
    def GET(self):
        note_id = xutils.get_argument("id")
        version = xutils.get_argument("version")
        
        creator = xauth.current_name()
        note = NOTE_DAO.get_by_id_creator(note_id, creator)
        content = ""
        if note != None:
            note = xutils.call("note.get_history", note_id, version)
            if note != None:
                content = note.content
        return dict(code = "success", data = content)


class NoticeHandler:
    """TODO 提醒的功能重新基于数据库来实现"""

    @xauth.login_required()
    def GET(self):
        # 刷新提醒,上下文为空
        user_name = xauth.current_name()
        offset    = 0
        limit     = 200
        orderby   = "ctime_desc"

        xmanager.fire("notice.update")
        # files  = NOTE_DAO.list_by_type(user_name, "list", offset, limit, orderby)
        return xtemplate.render("note/page/notice.html")

class QueryHandler:

    @xauth.login_required("admin")
    def GET(self, action = ""):
        if action == "get_by_id":
            id = xutils.get_argument("id")
            return dict(code = "success", data = NOTE_DAO.get_by_id(id))
        if action == "get_by_name":
            name = xutils.get_argument("name")
            return dict(code = "success", data = NOTE_DAO.get_by_name(xauth.current_name(), name))
        return dict(code="fail", message = "unknown action")

class GetDialogHandler:

    def get_group_option_dialog(self, kw):
        note_id = xutils.get_argument("note_id")
        file    = NOTE_DAO.get_by_id(note_id)
        kw.file = file

    def get_share_group_dialog(self, kw):
        user_name = xauth.current_name()
        note_id = xutils.get_argument("note_id")
        file    = NOTE_DAO.get_by_id(note_id)
        kw.file = file
        kw.share_to_list = []

        if file != None:
            share_from_info = NOTE_DAO.get_share_from(user_name, file.id)
            if share_from_info != None:
                kw.share_to_list = share_from_info.share_to_list


    @xauth.login_required()
    def GET(self, name = ""):
        kw = Storage()

        if name == "group_option_dialog":
            self.get_group_option_dialog(kw)

        if name == "share_group_dialog":
            self.get_share_group_dialog(kw)

        return xtemplate.render("note/ajax/%s.html" % name, **kw)

xurls = (
    r"/note/(edit|view)"   , ViewHandler,
    r"/note/print"         , PrintHandler,
    r"/note/(\d+)"         , ViewByIdHandler,
    r"/note/view/([\w\-]+)", ViewByIdHandler,
    r"/note/history"       , NoteHistoryHandler,
    r"/note/history_view"  , HistoryViewHandler,
    r"/note/notice"        , NoticeHandler,
    r"/note/query/(\w+)"   , QueryHandler,
    r"/note/ajax/(.+)"     , GetDialogHandler,
    r"/file/mark"          , MarkHandler,
    r"/file/unmark"        , UnmarkHandler,
    r"/file/markdown"      , ViewHandler
)

