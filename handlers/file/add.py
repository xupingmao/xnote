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
        file.size      = len(content)

        code = "fail"
        error = ""
        try:
            db = xtables.get_file_table()
            if name != '':
                f = db.select_one(where=dict(name=name,is_deleted=0))
                if f != None:
                    key = name
                    raise Exception(u"%s 已存在" % name)
                # 分组提前
                if file.type == "group":
                    file.priority = 1
                inserted_id = db.insert(**file)                
                # 更新分组下面页面的数量
                dao.update_children_count(parent_id, db = db)
                if _type == "json":
                    return dict(code="success", id=inserted_id)
                raise web.seeother("/file/view?id={}".format(inserted_id))
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

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "")
        name = xutils.get_argument("name", "")
        file = None

        if id == "" and name == "":
            return dict(code="fail", message="id,name至少一个不为空")

        db = xtables.get_file_table()
        if id != "":
            file = db.select_one(where=dict(id=int(id)))
        else:
            file = db.select_one(where=dict(name=name))
        if file is None:
            return dict(code="fail", message="文件不存在")
        id = file.id

        if not xauth.is_admin() and file.creator != xauth.get_current_name():
            return dict(code="fail", message="没有删除权限")

        if file.type == "group":
            children_count = db.count(where="parent_id=%s AND is_deleted=0"%id)
            if children_count > 0:
                return dict(code="fail", message="分组不为空")

        db.update(is_deleted=1, mtime=dateutil.format_time(), where=dict(id=int(id)))
        db.delete(where="is_deleted=1 AND mtime < $date", vars=dict(date=dateutil.before(days=30,format=True)))
        return dict(code="success")
        
    def POST(self):
        return self.GET()

xurls = (
    r"/file/add", AddHandler,
    r"/file/remove", RemoveHandler
)


