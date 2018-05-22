# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2017
# @modified 2018/05/22 22:20:20

"""Description here"""
import web
import time
import xauth
import xutils
import xtemplate
import xtables
import xmanager
from xutils import Storage
from xutils import dateutil

def get_by_name(db, name):
    return db.select_one(where=dict(name = name, is_deleted = 0, creator = xauth.get_current_name()))


def get_pathlist(db, parent_id, limit = 2):
    file = db.select_one(where=dict(id = parent_id))
    pathlist = []
    while file is not None:
        file.url = "/note/view?id=%s" % file.id
        pathlist.insert(0, file)
        if len(pathlist) >= limit:
            break
        if file.parent_id == 0:
            break
        else:
            file = db.select_one(where=dict(id=file.parent_id))
    return pathlist

def update_children_count(parent_id, db=None):
    if parent_id is None or parent_id == "":
        return
    if db is None:
        db = get_file_db()
    group_count = db.count(where="parent_id=$parent_id AND is_deleted=0", vars=dict(parent_id=parent_id))
    db.update(size=group_count, where=dict(id=parent_id))

class AddHandler:

    @xauth.login_required()
    def POST(self):
        name = xutils.get_argument("name", "")
        tags = xutils.get_argument("tags", "")
        key  = xutils.get_argument("key", "")
        content = xutils.get_argument("content", "")
        type    = xutils.get_argument("type", "post")
        format   = xutils.get_argument("_format", "")
        parent_id = xutils.get_argument("parent_id", 0, type=int)

        if key == "":
            key = time.strftime("%Y.%m.%d")

        file = Storage(name = name)
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
                f = get_by_name(db, name)
                if f != None:
                    key = name
                    raise Exception(u"%s 已存在" % name)
                # 分组提前
                if file.type == "group":
                    file.priority = 1
                file_dict = dict(**file)
                del file_dict["default_value"]
                inserted_id = db.insert(**file_dict)                
                # 更新分组下面页面的数量
                update_children_count(parent_id, db = db)
                xmanager.fire("note.add", dict(name=name))
                if format == "json":
                    return dict(code="success", id=inserted_id)
                raise web.seeother("/file/view?id={}".format(inserted_id))
        except web.HTTPError as e1:
            raise e1
        except Exception as e:
            xutils.print_exc()
            error = str(e)
        return xtemplate.render("note/add.html", key = "", 
            name = key, tags = tags, error=error,
            pathlist = get_pathlist(db, parent_id),
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
            file = db.select_one(where=dict(id=int(id), is_deleted=0))
        elif name != "":
            file = get_by_name(db, name)
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
        xmanager.fire("note.remove", dict(id=id))
        return dict(code="success")
        
    def POST(self):
        return self.GET()

class DictPutHandler:

    def GET(self):
        return self.POST()

    @xauth.login_required()
    def POST(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")
        db = xtables.get_dict_table()
        item = db.select_one(where=dict(key=key))
        current = xutils.format_datetime()
        if key == "" or key is None:
            return dict(code="fail", message="key is empty")
        if item is None:
            db.insert(key=key, value=value, ctime = current, mtime = current)
        else:
            db.update(value = value, mtime = current, where = dict(key=key))
        return db.select_one(where=dict(key=key))

class RenameHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        name = xutils.get_argument("name")
        if name == "" or name is None:
            return dict(code="fail", message="名称为空")
        db = xtables.get_file_table()
        old  = db.select_one(where=dict(id=id))
        if old.creator != xauth.get_current_name():
            return dict(code="fail", message="没有权限")

        file = db.select_one(where=dict(name=name))
        if file is not None:
            return dict(code="fail", message="%r已存在" % name)
        db.update(where=dict(id=id), name=name, mtime=xutils.format_datetime())
        event_body = dict(action="rename", id=id, name=name)
        xmanager.fire("note.updated", event_body)
        xmanager.fire("note.rename", event_body)
        return dict(code="success")

    def GET(self):
        return self.POST()

xurls = (
    r"/file/add", AddHandler,
    r"/note/add", AddHandler,
    r"/file/remove", RemoveHandler,
    r"/note/remove", RemoveHandler,
    r"/file/dict/put", DictPutHandler,
    r"/file/rename", RenameHandler,
)


