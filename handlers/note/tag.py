# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2018/06/20 21:58:09
import math
import xutils
import xtemplate
import xauth
import xtables
import xconfig

class TagHandler:
    
    def GET(self, id):
        id        = int(id)
        db        = xtables.get_file_tag_table()
        file_tags = db.select(where=dict(file_id=id))
        return dict(code="", message="", data=list(file_tags))

class UpdateTagHandler:

    @xauth.login_required()
    def POST(self):
        from . import dao
        id       = xutils.get_argument("file_id", type=int)
        tags_str = xutils.get_argument("tags")
        tag_db   = xtables.get_file_tag_table()
        
        if tags_str is None or tags_str == "":
            tag_db.delete(where=dict(file_id=id))
            return dict(code="success")
        new_tags = set(tags_str.split(" "))
        file     = dao.get_by_id(id)
        db       = dao.get_file_db()
        file_db  = xtables.get_file_table()
        # 求出两个差集进行运算
        old_tags = tag_db.select(where=dict(file_id=id))
        old_tags = set([v.name for v in old_tags])

        to_delete = old_tags - new_tags
        to_add    = new_tags - old_tags

        for item in to_delete:
            tag_db.delete(where=dict(name=item, file_id=id))
        for item in to_add:
            if item == "": continue
            tag_db.insert(name=item, file_id=id)

        file_db.update(related=tags_str, where=dict(id=id))
        return dict(code="", message="", data="OK")

    def GET(self):
        return self.POST()

class TagNameHandler:

    @xauth.login_required()
    def GET(self, tagname):
        from . import dao
        tagname  = xutils.unquote(tagname)
        db       = xtables.get_file_table()
        page     = xutils.get_argument("page", 1, type=int)
        limit    = xutils.get_argument("limit", 10, type=int)
        offset   = (page-1) * limit
        pagesize = xconfig.PAGE_SIZE
        role = "admin"

        if role == "admin":
            count_sql = "SELECT COUNT(1) AS amount FROM file_tag WHERE LOWER(name) = $name"
            sql = "SELECT f.* FROM file f, file_tag ft ON ft.file_id = f.id WHERE LOWER(ft.name) = $name ORDER BY f.ctime DESC LIMIT $offset, $limit"
        else:
            count_sql = "SELECT COUNT(1) AS amount FROM file_tag WHERE LOWER(name) = $name AND groups IN $groups"
            sql = "SELECT f.* FROM file f, file_tag ft ON ft.file_id = f.id WHERE LOWER(ft.name) = $name AND f.groups IN $groups ORDER BY f.ctime DESC LIMIT $offset, $limit"
        groups = ["*", role]
        count = db.query(count_sql, vars=dict(name=tagname.lower(), groups=groups))[0].amount

        files = db.query(sql,
            vars=dict(name=tagname.lower(), offset=offset, limit=limit, groups=groups))
        files = [dao.FileDO.fromDict(f) for f in files]
        return xtemplate.render("note/tagname.html", 
            tagname  =tagname, 
            files    =files, 
            page_max =math.ceil(count / pagesize), 
            page     =page)

@xutils.cache(key="tag.get_taglist", expire=60)
def get_taglist(db, user_name):
    groups = ["*", user_name]
    sql = "SELECT LOWER(name) AS name, COUNT(*) AS amount FROM file_tag GROUP BY LOWER(name) ORDER BY amount DESC, name ASC";
    tag_list = db.query(sql, vars = dict(groups = groups))
    return list(tag_list)

class TagListHandler:

    @xauth.login_required()
    def GET(self):
        db        = xtables.get_file_table()
        user_name = xauth.get_current_name()
        tag_list  = get_taglist(db, user_name)
        return xtemplate.render("note/taglist.html", tag_list = tag_list)

xurls = (
    r"/file/tag/(\d+)"   , TagHandler,
    r"/file/tag/update"  , UpdateTagHandler,
    r"/file/tagname/(.*)", TagNameHandler,
    r"/file/taglist"     , TagListHandler
)

