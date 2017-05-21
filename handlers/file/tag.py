# encoding=utf-8
# Created by xupingmao on 2017/04/16

from . import dao
import xutils

class TagHandler:
    
    def GET(self, id):
        id   = int(id)
        file = dao.get_by_id(id)
        db   = dao.get_file_db()

        file_tags = db.select("file_tag", where=dict(file_id=id,groups=file.groups))
        return dict(code="", message="", data=list(file_tags))

class AddTagHandler:

    def POST(self):
        id   = xutils.get_argument("file_id", type=int)
        tags_str = xutils.get_argument("tags")
        tags = tags_str.split(" ")
        file = dao.get_by_id(id)
        db   = dao.get_file_db()
        # 先删除所有的tag，再增加
        db.delete("file_tag", where=dict(file_id=id, groups=file.groups))
        added = set()
        for tag in tags:
            if tag == "":
                continue
            if tag in added:
                continue
            added.add(tag)
            # t = TagEntity(id, tag, "*")
            db.insert("file_tag", file_id=id, name=tag, groups=file.groups)
        return dict(code="", message="", data="OK")

class TagListHandler:

    def GET(self, tagname):
        db = dao.get_file_db()
        tag_list = db.select("file_tag", where="UPPER(name) = $name", vars=dict(name=tagname.upper()))
        return dict(code="", message="", data=list(tag_list))

xurls = (r"/file/tag/(\d+)", TagHandler,
         r"/file/tag/add", AddTagHandler,
         r"/file/taglist/(.*)", TagListHandler)

