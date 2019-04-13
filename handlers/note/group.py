# encoding=utf-8
# @since 2016/12
# @modified 2019/04/13 23:40:59
import math
import time
import web
import xutils
import xtemplate
import xtables
import xauth
import xconfig
import xmanager
from xutils import Storage
from xutils import cacheutil, dateutil
from xutils.dateutil import Timer
from xtemplate import T

VIEW_TPL = "note/view.html"

def update_children_count(parent_id, db=None):
    if parent_id is None or parent_id == "":
        return
    group_count = db.count(where="parent_id=$parent_id AND is_deleted=0", vars=dict(parent_id=parent_id))
    db.update(size=group_count, where=dict(id=parent_id))

class PathNode:

    def __init__(self, name, url):
        self.name = name
        self.url = url

class Ungrouped:

    @xauth.login_required()
    def GET(self):
        page           = xutils.get_argument("page", 1, type=int)
        db             = xtables.get_file_table()
        user_name      = xauth.get_current_name()
        pagesize       = xconfig.PAGE_SIZE
        vars           = dict()
        vars["name"]   = user_name
        vars["offset"] = (page-1) * pagesize
        vars["limit"]  = pagesize

        sql = """SELECT a.* FROM file a LEFT JOIN file b ON a.parent_id = b.id 
            WHERE a.is_deleted = 0 
                AND a.type != 'group' 
                AND a.creator = $name AND (b.id is null OR b.type != 'group') 
            ORDER BY mtime DESC LIMIT $offset, $limit"""
        files = db.query(sql, vars=vars)
        
        count_sql = """SELECT COUNT(1) AS amount FROM file a LEFT JOIN file b ON a.parent_id = b.id 
            WHERE a.is_deleted = 0 
                AND a.type != 'group' 
                AND a.creator = $name
                AND (b.id is null OR b.type != 'group')"""
        amount = db.count(sql = count_sql, vars = vars)

        return xtemplate.render(VIEW_TPL,
            show_aside = True,
            file_type  = "group",
            pathlist   = [Storage(name="未分类", type="group", url="/note/ungrouped")],
            files      = files,
            file       = Storage(name="未分类", type="group"),
            page       = page,
            page_max   = math.ceil(amount / pagesize),
            groups     = xutils.call("note.list_group"),
            show_mdate = True,
            page_url   = "/note/ungrouped?page=")

class MoveHandler:
    
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        parent_id = xutils.get_argument("parent_id", "", type=int)
        db = xtables.get_file_table()
        file = db.select_first(where=dict(id=id))
        if file is None:
            return dict(code="fail", message="file not exists")
        db.update(parent_id=parent_id, where=dict(id=id))
        update_children_count(file.parent_id, db=db)
        update_children_count(parent_id, db=db)
        return dict(code="success")

    def POST(self):
        return self.GET()
        
class GroupListHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        data = xutils.call("note.list_group", xauth.get_current_name())
        ungrouped_count = xtables.get_file_table().count(where="creator=$creator AND parent_id=0 AND is_deleted=0 AND type!='group'", 
            vars=dict(creator=xauth.get_current_name()))
        return xtemplate.render(VIEW_TPL,
            ungrouped_count = ungrouped_count,
            file_type       = "group_list",
            pseudo_groups   = True,
            show_search_div = True,
            show_add_group  = True,
            files           = data)

class GroupSelectHandler:
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        filetype = xutils.get_argument("filetype", "")
        data = xutils.call("note.list_group", xauth.get_current_name())
        web.header("Content-Type", "text/html; charset=utf-8")
        return xtemplate.render("note/group_select.html", 
            id=id, filelist=data, file_type="group")



class RemovedHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_file_table()
        files = db.select(where="is_deleted=1", order="ctime DESC", offset=(page-1)*10, limit=10)
        amount = db.count(where="is_deleted=1")

        return xtemplate.render(VIEW_TPL,
            pathlist  = [PathNode("回收站", "/note/removed")],
            file_type = "group",
            files     = files,
            page      = page,
            page_max  = math.ceil(amount / 10),
            page_url  = "/note/removed?page=")

class RecentHandler:
    """show recent notes"""

    @xauth.login_required()
    def GET(self, orderby = "edit"):
        if not xauth.has_login():
            raise web.seeother("/note/public")
        if xutils.sqlite3 is None:
            raise web.seeother("/fs_list")
        days     = xutils.get_argument("days", 30, type=int)
        page     = xutils.get_argument("page", 1, type=int)
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page     = max(1, page)
        offset   = max(0, (page-1) * pagesize)
        limit    = pagesize
        time_attr = "ctime"

        creator = xauth.get_current_name()
        if orderby == "viewed":
            html_title = "Recent Viewed"
            files = xutils.call("note.list_recent_viewed", creator, offset, limit)
            time_attr = "atime"
        elif orderby == "created":
            html_title = "Recent Created"
            files = xutils.call("note.list_recent_created", None, offset, limit)
            time_attr = "ctime"
        else:
            html_title = "Recent Updated"
            files = xutils.call("note.list_recent_edit", None, offset, limit)
            time_attr = "mtime"
        
        groups  = xutils.call("note.list_group", creator)
        count   = xutils.call("note.count_user_note", creator)

        return xtemplate.render("note/recent.html", 
            html_title  = html_title,
            pathlist    = [Storage(name=T(html_title), type="group", url="/note/recent_" + orderby)],
            file_type   = "group",
            files       = files, 
            file        = Storage(name=T(html_title), type="group"),
            groups      = groups,
            show_notice = False,
            show_mdate  = True,
            show_groups = False,
            show_aside  = True,
            page        = page, 
            time_attr   = time_attr,
            page_max    = math.ceil(count/xconfig.PAGE_SIZE), 
            page_url    ="/note/recent_%s?page=" % orderby)


class PublicGroupHandler:

    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        db = xtables.get_file_table()
        where = "is_deleted=0 AND is_public=1"
        files = db.select(where=where, offset=(page-1)*xconfig.PAGE_SIZE, limit=xconfig.PAGE_SIZE, order="ctime DESC")
        count = db.count(where=where)
        return xtemplate.render(VIEW_TPL, 
            show_aside = True,
            pathlist   = [Storage(name="分享笔记", url="/note/public")],
            file_type  = "group",
            files      = files,
            page       = page, 
            show_cdate = True,
            groups     = xutils.call("note.list_group"),
            page_max   = math.ceil(count/xconfig.PAGE_SIZE), 
            page_url   = "/note/public?page=")

def link_by_month(year, month, delta = 0):
    tm = Storage(tm_year = year, tm_mon = month, tm_mday = 0)
    t_year, t_mon, t_day = dateutil.date_add(tm, months = delta)
    return "/note/date?year=%d&month=%02d" % (t_year, t_mon)

class DateHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        
        year  = xutils.get_argument("year", time.strftime("%Y"))
        month = xutils.get_argument("month", time.strftime("%m"))
        if len(month) == 1:
            month = '0' + month

        date = year + "-" + month
        created = xutils.call("note.list_by_date", "ctime", user_name, date)
        by_name = xutils.call("note.list_by_date", "name", user_name, year + "_" + month)

        notes = []
        dup = set()
        for v in created + by_name:
            if v.id in dup:
                continue
            dup.add(v.id)
            notes.append(v)

        return xtemplate.render("note/list_by_date.html", 
            show_aside = True,
            link_by_month = link_by_month,
            year = int(year),
            month = int(month),
            notes = notes)

xurls = (
    r"/note/group"          , GroupListHandler,
    r"/note/ungrouped"      , Ungrouped,
    r"/note/public"         , PublicGroupHandler,
    r"/note/removed"        , RemovedHandler,
    r"/note/recent_(created)" , RecentHandler,
    r"/note/recent_edit"    , RecentHandler,
    r"/note/recent_(viewed)", RecentHandler,
    r"/note/group/move"     , MoveHandler,
    r"/note/group/select"   , GroupSelectHandler,
    r"/note/date"           , DateHandler,
    r"/note/monthly"        , DateHandler,
    
    r"/file/group/removed"  , RemovedHandler,
    r"/file/group/list"     , GroupListHandler,
    r"/file/group/move"     , MoveHandler,
    r"/file/recent_edit"    , RecentHandler,
)

