# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12
# @modified 2019/08/03 15:56:09
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
config = xconfig

PAGE_SIZE = xconfig.PAGE_SIZE

@xmanager.listen("note.view", is_async=True)
def visit_by_id(ctx):
    id = ctx.id
    xutils.call("note.visit", id)

class ViewHandler:

    xconfig.note_history = History("笔记浏览记录", 200)

    @xutils.timeit(name = "Note.View", logfile = True)
    def GET(self, op):
        id            = xutils.get_argument("id", "")
        name          = xutils.get_argument("name", "")
        page          = xutils.get_argument("page", 1, type=int)
        pagesize      = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        show_menu     = xutils.get_argument("show_menu", "true") != "false"
        orderby       = xutils.get_argument("orderby", "mtiem_desc")
        user_name     = xauth.get_current_name()
        show_add_file = False
        title         = None
        show_pagination = True
        show_search_div = False

        if id == "0":
            raise web.found("/")
        # 回收站的笔记也能看到
        if id == "" and name == "":
            raise HTTPError(504)
        if id != "":
            file = xutils.call("note.get_by_id", id)
        elif name is not None:
            file = xutils.call("note.get_by_name", name, db=db)
        if file is None:
            raise web.notfound()
        
        if file.type != "group" and not file.is_public and user_name != "admin" and user_name != file.creator:
            raise web.seeother("/unauthorized")
        pathlist        = xutils.call("note.list_path", file)
        can_edit        = (file.creator == user_name) or (user_name == "admin")
        role            = xauth.get_current_role()

        # 定义一些变量
        show_groups    = False
        show_mdate     = False
        files          = []
        recent_created = []
        groups         = []
        amount         = 0
        show_recommend = False
        template_name  = "note/view.html"
        next_note      = None
        prev_note      = None
        filelist       = None
        xconfig.note_history.put(dict(user=user_name, 
            link = "/note/view?id=%s" % id, 
            name = file.name))
        recommended_notes = []

        title  = file.name
        if file.type == "group":
            files  = xutils.call("note.list_by_parent", user_name, file.id, (page-1)*pagesize, pagesize, orderby)
            amount = xutils.call("note.count", user_name, file.id)
            content         = file.content
            show_search_div = True
            show_add_file   = True
            show_mdate      = True
        elif file.type == "md" or file.type == "text":
            content = file.content
            show_recommend = True
            show_pagination = False
            if op == "edit":
                show_recommend = False
                template_name = "note/editor/markdown_edit.html"
        else:
            content = file.content
            content = content.replace(u'\xad', '\n')
            content = content.replace(u'\n', '<br/>')
            file.data = file.data.replace(u"\xad", "\n")
            file.data = file.data.replace(u'\n', '<br/>')
            if file.data == None or file.data == "":
                file.data = content
            show_recommend = True
            show_pagination = False

        fpath = os.path.join(xconfig.UPLOAD_DIR, file.creator, str(file.parent_id), str(id))

        # 处理相册
        if file.type == "gallery":
            if os.path.exists(fpath):
                filelist = fsutil.list_files(fpath, webpath = True)
            else:
                filelist = []
            file.path = fpath

        if show_recommend and user_name is not None:
            show_groups = False
            # 推荐系统
            ctx = Storage(id=file.id, name = file.name, creator = file.creator, 
                content = file.content,
                parent_id = file.parent_id,
                result = [])
            xmanager.fire("note.recommend", ctx)
            recommended_notes = ctx.result

            next_note = xutils.call("note.find_next_note", file, user_name)
            prev_note = xutils.call("note.find_prev_note", file, user_name)
        
        xmanager.fire("note.view", file)
        show_aside = True
        if op == "edit":
            show_aside = False

        return xtemplate.render(template_name,
            show_aside    = show_aside,
            html_title    = title,
            file          = file, 
            path          = fpath,
            filelist      = filelist,
            note_id       = id,
            op            = op,
            show_mdate    = show_mdate,
            show_add_file = show_add_file,
            show_menu     = show_menu,
            show_pagination = show_pagination,
            can_edit = can_edit,
            pathlist = pathlist,
            page_max = math.ceil(amount/pagesize),
            page     = page,
            page_url = "/note/view?id=%s&orderby=%s&page=" % (id, orderby),
            files    = files, 
            recent_created    = recent_created,
            show_groups       = show_groups,
            groups            = groups,
            prev_note         = prev_note,
            next_note         = next_note,
            recommended_notes = recommended_notes)

class PrintHandler:

    @xauth.login_required()
    def GET(self):
        id        = xutils.get_argument("id")
        file      = xutils.call("note.get_by_id", id)
        user_name = xauth.current_name()
        if file.is_public != 1 and user_name != "admin" and user_name != file.creator:
            raise web.seeother("/unauthorized")
        return xtemplate.render("note/print.html", show_menu = False, note = file)

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
        note = xutils.call("note.get_by_id_creator", note_id, creator)
        if note is None:
            history_list = []
        else:
            history_list = xutils.call("note.list_history", note_id)
        return xtemplate.render("note/history_list.html", 
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



xurls = (
    r"/note/(edit|view)"   , ViewHandler,
    r"/note/print"         , PrintHandler,
    r"/note/dict"          , DictHandler,
    r"/note/history"       , NoteHistoryHandler,
    r"/note/history_view"  , HistoryViewHandler,
    
    r"/file/(\d+)/upvote"  , Upvote,
    r"/file/(\d+)/downvote", Downvote,
    r"/file/mark"          , MarkHandler,
    r"/file/unmark"        , UnmarkHandler,
    r"/file/markdown"      , ViewHandler
)

