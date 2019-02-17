# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12
# @modified 2019/02/17 18:17:23
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
        show_menu     = xutils.get_argument("show_menu", "true") != "false"
        db            = xtables.get_file_table()
        user_name     = xauth.get_current_name()
        show_add_file = False
        title         = None
        show_pagination = True
        show_search_div = False

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
        pathlist        = dao.get_pathlist(db, file)
        can_edit        = (file.creator == user_name) or (user_name == "admin")
        role            = xauth.get_current_role()

        # 定义一些变量
        show_groups    = True
        show_mdate     = False
        files          = []
        recent_created = []
        amount         = 0
        show_recommend = False
        template_name  = "note/view.html"
        xconfig.note_history.put(dict(user=user_name, 
            link = "/note/view?id=%s" % id, 
            name = file.name))
        recommended_notes = []

        title  = file.name
        groups = xutils.call("note.list_group")
        if file.type == "group":
            where_sql = "parent_id=$parent_id AND is_deleted=0 AND (creator=$creator OR is_public=1)"
            if xauth.is_admin():
                where_sql = "parent_id=$parent_id AND is_deleted=0"
            amount = db.count(where = where_sql,
                vars=dict(parent_id=file.id, creator=user_name))
            files = db.select(where = where_sql, 
                vars = dict(parent_id=file.id, is_deleted=0, creator=user_name), 
                order = "name", 
                limit = pagesize, 
                offset = (page-1)*pagesize)
            content         = file.content
            show_search_div = True
            show_add_file   = True
            show_mdate      = True
            # recent_created  = xutils.call("note.list_recent_created", file.id, 10)
        elif file.type == "md" or file.type == "text":
            content = file.content
            if op == "edit":
                template_name = "note/markdown_edit.html"
            show_recommend = True
            show_pagination = False
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

        if show_recommend:
            show_groups = False
            # 推荐系统
            ctx = Storage(id=file.id, name = file.name, creator = file.creator, 
                content = file.content,
                parent_id = file.parent_id,
                result = [])
            xmanager.fire("note.recommend", ctx)
            recommended_notes = ctx.result
        
        xmanager.fire("note.view", file)
        show_aside = True
        if op == "edit":
            show_aside = False
        return xtemplate.render(template_name,
            show_aside    = show_aside,
            html_title    = title,
            file          = file, 
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
            page_url = "/note/view?id=%s&page=" % id,
            files    = files, 
            recent_created = recent_created,
            show_groups = show_groups,
            groups   = groups,
            recommended_notes = recommended_notes)

class PrintHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        db = xtables.get_file_table()
        file = dao.get_by_id(id, db=db)
        user_name = xauth.get_current_name()
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

xurls = (
    r"/note/(edit|view)"   , ViewHandler,
    r"/note/print"         , PrintHandler,
    r"/note/dict"          , DictHandler,
    
    r"/file/(edit|view)"   , ViewHandler, 
    r"/file/(\d+)/upvote"  , Upvote,
    r"/file/(\d+)/downvote", Downvote,
    r"/file/mark"          , MarkHandler,
    r"/file/unmark"        , UnmarkHandler,
    r"/file/markdown"      , ViewHandler
)

