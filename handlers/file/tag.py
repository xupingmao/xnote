# encoding=utf-8
# Created by xupingmao on 2017/04/16

from . import dao
import xutils
import xtemplate
import xauth
import xtables

class TagHandler:
    
    def GET(self, id):
        id   = int(id)
        db   = xtables.get_file_tag_table()
        file_tags = db.select(where=dict(file_id=id))
        return dict(code="", message="", data=list(file_tags))

class AddTagHandler:

    def POST(self):
        id   = xutils.get_argument("file_id", type=int)
        tags_str = xutils.get_argument("tags")
        tags = tags_str.split(" ")
        file = dao.get_by_id(id)
        db   = dao.get_file_db()
        file_db = xtables.get_file_table()
        # 先删除所有的tag，再增加
        db.delete("file_tag", where=dict(file_id=id))
        added = set()
        for tag in tags:
            if tag == "":
                continue
            if tag in added:
                continue
            added.add(tag)
            # t = TagEntity(id, tag, "*")
            db.insert("file_tag", file_id=id, name=tag)
        file_db.update(related=tags_str, where=dict(id=id))
        return dict(code="", message="", data="OK")

class TagNameHandler:

    @xauth.login_required()
    def GET(self, tagname):
        tagname = xutils.unquote(tagname)
        db = dao.get_file_db()
        page   = xutils.get_argument("page", 1, type=int)
        limit  = xutils.get_argument("limit", 10, type=int)
        offset = (page-1) * limit

        # role = xauth.get_current_role()
        role = "admin"

        if role == "admin":
            count_sql = "SELECT COUNT(1) AS amount FROM file_tag WHERE UPPER(name) = $name"
            sql = "SELECT f.* FROM file f, file_tag ft ON ft.file_id = f.id WHERE UPPER(ft.name) = $name ORDER BY f.ctime DESC LIMIT $offset, $limit"
        else:
            count_sql = "SELECT COUNT(1) AS amount FROM file_tag WHERE UPPER(name) = $name AND groups IN $groups"
            sql = "SELECT f.* FROM file f, file_tag ft ON ft.file_id = f.id WHERE UPPER(ft.name) = $name AND f.groups IN $groups ORDER BY f.ctime DESC LIMIT $offset, $limit"
        groups = ["*", role]
        # tag_list = db.select("file_tag", where="UPPER(name) = $name", vars=dict(name=tagname.upper()))
        count = db.query(count_sql, vars=dict(name=tagname.upper(), groups=groups))[0].amount

        files = db.query(sql,
            vars=dict(name=tagname.upper(), offset=offset, limit=limit, groups=groups))
        files = [dao.FileDO.fromDict(f) for f in files]
        return xtemplate.render("file/tagname.html", tagname=tagname, files=files, count=count, page=page)
        # return dict(code="", message="", data=list(tag_list))

class TagListHandler:

    @xauth.login_required()
    def GET(self):
        db = dao.get_file_db()
        user_name = xauth.get_current_role()
        # if user_name == "admin":
        #     sql = "SELECT name, COUNT(*) AS amount FROM file_tag GROUP BY name ORDER BY amount DESC, name ASC";
        # else:
        #     sql = "SELECT name, COUNT(*) AS amount FROM file_tag WHERE groups in $groups GROUP BY name ORDER BY amount DESC, name ASC";
        groups = ["*", user_name]
        sql = "SELECT name, COUNT(*) AS amount FROM file_tag GROUP BY name ORDER BY amount DESC, name ASC";

        tag_list = db.query(sql, vars = dict(groups = groups))
        return xtemplate.render("file/taglist.html", tag_list = list(tag_list))
        # return dict(code="", message="", data=tag_list)

xurls = (r"/file/tag/(\d+)", TagHandler,
         r"/file/tag/add", AddTagHandler,
         r"/file/tagname/(.*)", TagNameHandler,
         r"/file/taglist", TagListHandler)

