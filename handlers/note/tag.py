# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2019/05/01 02:13:09
import math
import xutils
import xtemplate
import xauth
import xtables
import xconfig
from xutils import Storage

class TagHandler:
    
    def GET(self, id):
        note = xutils.call("note.get_by_id", id)
        tags = None
        if note:
            tags = [Storage(name=name) for name in note.tags]
        if not isinstance(tags, list):
            tags = []
        return dict(code="", message="", data=tags)

class UpdateTagHandler:

    @xauth.login_required()
    def POST(self):
        id        = xutils.get_argument("file_id")
        tags_str  = xutils.get_argument("tags")
        tag_db    = xtables.get_file_tag_table()
        user_name = xauth.get_current_name()
        note      = xutils.call("note.get_by_id", id)

        if tags_str is None or tags_str == "":
            # tag_db.delete(where=dict(file_id=id, user=user_name))
            xutils.call("note.update", dict(id = id, creator = user_name), tags = [])
            return dict(code="success")
        new_tags = tags_str.split(" ")
        xutils.call("note.update", dict(id = id, creator = user_name), tags = new_tags)
        return dict(code="success", message="", data="OK")

    def GET(self):
        return self.POST()

class TagNameHandler:

    def GET(self, tagname):
        from . import dao
        tagname  = xutils.unquote(tagname)
        db       = xtables.get_file_table()
        page     = xutils.get_argument("page", 1, type=int)
        limit    = xutils.get_argument("limit", 10, type=int)
        offset   = (page-1) * limit
        pagesize = xconfig.PAGE_SIZE

        if xauth.has_login():
            user_name = xauth.get_current_name()
        else:
            user_name = ""
        count_sql = "SELECT COUNT(1) AS amount FROM file_tag WHERE LOWER(name) = $name AND (user=$user OR is_public=1)"
        sql = "SELECT f.* FROM file f, file_tag ft ON ft.file_id = f.id WHERE LOWER(ft.name) = $name AND (ft.user=$user OR ft.is_public=1) ORDER BY f.ctime DESC LIMIT $offset, $limit"
        count = db.query(count_sql, vars=dict(name=tagname.lower(), user=user_name))[0].amount

        files = db.query(sql,
            vars=dict(name=tagname.lower(), offset=offset, limit=limit, user=user_name))
        files = [dao.FileDO.fromDict(f) for f in files]
        return xtemplate.render("note/tagname.html", 
            show_aside = True,
            tagname    = tagname, 
            files      = files, 
            show_mdate = True,
            page_max   = math.ceil(count / pagesize), 
            page       = page)


class TagListHandler:

    def GET(self):
        if xauth.has_login():
            user_name = xauth.get_current_name()
            tag_list  = xutils.call("note.list_tag", user_name)
        else:
            tag_list  = xutils.call("note.list_tag", "")
        return xtemplate.render("note/taglist.html", 
            show_aside = True,
            tag_list = tag_list)

xurls = (
    r"/note/tag/(\d+)"   , TagHandler,
    r"/note/tag/update"  , UpdateTagHandler,
    r"/note/tagname/(.*)", TagNameHandler,
    r"/note/taglist"     , TagListHandler
)

