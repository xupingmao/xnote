# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017
# 

"""Description here"""
import web
import time
from .dao import FileDO
from . import dao
from util import dateutil
import xauth
import xutils
import xtemplate
import xtables

class AddHandler:

    @xauth.login_required()
    def POST(self):
        name = xutils.get_argument("name", "")
        tags = xutils.get_argument("tags", "")
        key  = xutils.get_argument("key", "")
        content = xutils.get_argument("content", "")
        type    = xutils.get_argument("type", "post")
        _type   = xutils.get_argument("_type", "")
        parent_id = xutils.get_argument("parent_id", 0, type=int)

        if key == "":
            key = time.strftime("%Y.%m.%d")

        file = FileDO(name)
        file.atime   = xutils.format_datetime()
        file.mtime   = xutils.format_datetime()
        file.ctime   = xutils.format_datetime()
        file.creator = xauth.get_current_name()
        # 默认私有
        file.groups    = file.creator
        file.parent_id = parent_id
        file.type      = type
        file.content   = content

        code = "fail"
        error = ""
        try:
            if name != '':
                f = dao.get_by_name(name)
                if f != None:
                    key = name
                    raise Exception(u"%s 已存在" % name)
                # 分组提前
                if file.type == "group":
                    file.priority = 1
                f = dao.insert(file)
                inserted = dao.get_by_name(name)
                if _type == "json":
                    return dict(code="success", id=inserted.id)
                raise web.seeother("/file/view?id={}".format(inserted.id))
        except web.HTTPError as e1:
            raise e1
        except Exception as e:
            xutils.print_stacktrace()
            error = str(e)
        return xtemplate.render("file/add.html", key = "", 
            name = key, tags = tags, error=error,
            message = error,
            code = code)

    def GET(self):
        return self.POST()

class RemoveHandler:
    def remove_by_id(self, id):
        db = xtables.get_file_table()
        file = db.select_one(where=dict(id=int(id)))
        if file is None:
            return dict(code="fail", message="文件不存在")
        if file.type == "group":
            children_count = db.count(where="parent_id=%s AND is_deleted=0"%id)
            if children_count > 0:
                return dict(code="fail", message="分组不为空")
        db.update(is_deleted=1, mtime=dateutil.format_time(), where=dict(id=int(id)))
        db.delete(where="is_deleted=1 AND mtime < $date", vars=dict(date=dateutil.before(days=30,format=True)))
        return dict(code="success")

    def remove_by_name(self, name):
        db = xtables.get_file_table()
        file = db.select_one(where=dict(name=name))
        if file is None:
            return dict(code="success")
        db.update(is_deleted=1, where=dict(id=file.id))
        return dict(code="success")

    # 物理删除
    @xauth.login_required("admin")
    def GET(self):
        id = xutils.get_argument("id", "")
        name = xutils.get_argument("name", "")
        if id == "" and name == "":
            return dict(code="fail", message="id,name至少一个不为空")
        if id != "":
            return self.remove_by_id(int(id))
        return self.remove_by_name(name)
        
    def POST(self):
        return self.GET()

xurls = (
    r"/file/add", AddHandler,
    r"/file/remove", RemoveHandler
)


