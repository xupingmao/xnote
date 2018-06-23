# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12
# @modified 2018/06/23 19:49:36

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
from web import HTTPError
from . import dao
from xconfig import Storage
from xutils import History
config = xconfig

PAGE_SIZE = xconfig.PAGE_SIZE

@xmanager.listen("note.view", is_async=True)
def visit_by_id(ctx):
    id = ctx.id
    db = xtables.get_file_table()
    sql = "UPDATE file SET visited_cnt = visited_cnt + 1, atime=$atime where id = $id"
    db.query(sql, vars = dict(atime = xutils.format_datetime(), id=id))

class ViewHandler:

    xconfig.note_history = History("笔记浏览记录", 200)

    def GET(self, op):
        id            = xutils.get_argument("id", "")
        name          = xutils.get_argument("name", "")
        page          = xutils.get_argument("page", 1, type=int)
        pagesize      = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        db            = xtables.get_file_table()
        user_name     = xauth.get_current_name()
        show_add_file = False

        if id == "" and name == "":
            raise HTTPError(504)
        if id != "":
            id = int(id)
            file = dao.get_by_id(id, db=db)
        elif name is not None:
            file = dao.get_by_name(name, db=db)
        if file is None:
            raise web.notfound()
        if file.is_deleted == 1:
            raise web.seeother("/")
        
        if file.type != "group" and not file.is_public and user_name != "admin" and user_name != file.creator:
            raise web.seeother("/unauthorized")
        show_search_div = False
        pathlist        = dao.get_pathlist(db, file)
        can_edit        = (file.creator == user_name) or (user_name == "admin")
        role            = xauth.get_current_role()

        # 定义一些变量
        files          = []
        recent_created = []
        amount         = 0
        template_name  = "note/view.html"
        xconfig.note_history.put(dict(user=user_name, 
            link = "/note/view?id=%s" % id, 
            name = file.name))

        groups = xutils.call("note.list_group")
        if file.type == "group":
            where_sql = "parent_id=$parent_id AND is_deleted=0 AND (creator=$creator OR is_public=1)"
            if xauth.is_admin():
                where_sql = "parent_id=$parent_id AND is_deleted=0"
            amount = db.count(where = where_sql,
                vars=dict(parent_id=file.id, creator=user_name))
            files = db.select(where = where_sql, 
                vars=dict(parent_id=file.id, is_deleted=0, creator=user_name), 
                order="name", 
                limit=pagesize, 
                offset=(page-1)*pagesize)
            content         = file.content
            show_search_div = True
            show_add_file   = True
            recent_created  = xutils.call("note.list_recent_created", file.id, 10)
        elif file.type == "md" or file.type == "text":
            content = file.content
            if op == "edit":
                template_name = "note/markdown_edit.html"
            else:
                recent_created = xutils.call("note.list_recent_created", file.parent_id, 10)
        else:
            content = file.content
            content = content.replace(u'\xad', '\n')
            content = content.replace(u'\n', '<br/>')
            file.data = file.data.replace(u"\xad", "\n")
            file.data = file.data.replace(u'\n', '<br/>')
            if file.data == None or file.data == "":
                file.data = content
        
        xmanager.fire("note.view", file)
        return xtemplate.render(template_name,
            file=file, 
            op=op,
            show_add_file = show_add_file,
            can_edit = can_edit,
            pathlist = pathlist,
            page_max = math.ceil(amount/pagesize),
            page     = page,
            page_url = "/file/view?id=%s&page=" % id,
            files    = files, 
            recent_created = recent_created,
            groups   = groups)

def sqlite_escape(text):
    if text is None:
        return "NULL"
    if not (isinstance(text, str)):
        return repr(text)
    text = text.replace("'", "''")
    return "'" + text + "'"

def result(success = True, msg=None):
    return {"success": success, "result": None, "msg": msg}

def is_img(filename):
    name, ext = os.path.splitext(filename)
    return ext.lower() in (".gif", ".png", ".jpg", ".jpeg", ".bmp")

def get_link(filename, webpath):
    if is_img(filename):
        return "![%s](%s)" % (filename, webpath)
    return "[%s](%s)" % (filename, webpath)


class Upvote:

    @xauth.login_required()
    def GET(self, id):
        id = int(id)
        db = xtables.get_file_table()
        file = db.select_one(where=dict(id=int(id)))
        db.update(priority=1, where=dict(id=id))
        raise web.seeother("/file/view?id=%s" % id)

class Downvote:
    @xauth.login_required()
    def GET(self, id):
        id = int(id)
        db = xtables.get_file_table()
        file = db.select_one(where=dict(id=int(id)))
        db.update(priority=0, where=dict(id=id))
        raise web.seeother("/file/view?id=%s" % id)

class MarkHandler:

    def GET(self):
        id = xutils.get_argument("id")
        db = xtables.get_file_table()
        db.update(is_marked=1, where=dict(id=id))
        raise web.seeother("/file/view?id=%s"%id)

class UnmarkHandler:
    def GET(self):
        id = xutils.get_argument("id")
        db = xtables.get_file_table()
        db.update(is_marked=0, where=dict(id=id))
        raise web.seeother("/file/view?id=%s"%id)
        
class LibraryHandler:

    def GET(self):
        return xtemplate.render("note/library.html")

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
            return v
        items = map(convert, items)
        count = db.count()
        page_max = math.ceil(count / PAGE_SIZE)

        return xtemplate.render("note/view.html", 
            files = list(items), 
            file_type = "group",
            show_opts = False,
            page = page,
            page_max = page_max,
            page_url = "/file/dict?page=")

xurls = (
    r"/file/(edit|view)"   , ViewHandler, 
    r"/note/(edit|view)"   , ViewHandler,
    r"/file/(\d+)/upvote"  , Upvote,
    r"/file/(\d+)/downvote", Downvote,
    r"/file/mark"          , MarkHandler,
    r"/file/unmark"        , UnmarkHandler,
    r"/file/markdown"      , ViewHandler,
    r"/file/library"       , LibraryHandler,
    r"/file/dict"          , DictHandler
)

