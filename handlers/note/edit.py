# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2017
# @modified 2018/09/01 16:09:28

"""Description here"""
import os
import web
import time
import xauth
import xutils
import xtemplate
import xtables
import xmanager
import xconfig
from xutils import Storage
from xutils import dateutil
from xutils import cacheutil

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

def update_note_content(id, content, data=''):
    if id is None:
        return
    if content is None:
        content = ''
    if data is None:
        data = ''
    db = xtables.get_note_content_table()
    result = db.select_one(where=dict(id=id))
    if result is None:
        db.insert(id=id, content=content, data=data)
    else:
        db.update(where=dict(id=id), 
            content=content,
            data = data)

def update_note(db, where, **kw):
    note_id = where.get('id')
    content = kw.get('content')
    data = kw.get('data')

    kw["mtime"] = dateutil.format_time()
    # 处理乐观锁
    version = where.get("version")
    if version:
        kw["version"] = version + 1
    # 这两个字段废弃，移动到单独的表中
    if 'content' in kw:
        del kw['content']
        kw['content'] = ''
    if 'data' in kw:
        del kw['data']
        kw['data'] = ''
    rows = db.update(where = where, vars=None, **kw)
    if rows > 0:
        # 更新成功后再更新内容，不考虑极端的冲突情况
        update_note_content(note_id, content, data)
    return rows

@xmanager.listen(["note.add", "note.updated", "note.rename"])
def update_cache(ctx):
    type = ctx.get("type", "")
    cacheutil.prefix_del("recent_notes")
    cacheutil.prefix_del("group.list")

class AddHandler:

    @xauth.login_required()
    def POST(self):
        name      = xutils.get_argument("name", "")
        tags      = xutils.get_argument("tags", "")
        key       = xutils.get_argument("key", "")
        content   = xutils.get_argument("content", "")
        type      = xutils.get_argument("type", "post")
        format    = xutils.get_argument("_format", "")
        parent_id = xutils.get_argument("parent_id", 0, type=int)

        if key == "":
            key = time.strftime("%Y.%m.%d")

        file           = Storage(name = name)
        file.atime     = xutils.format_datetime()
        file.mtime     = xutils.format_datetime()
        file.ctime     = xutils.format_datetime()
        file.creator   = xauth.get_current_name()
        file.parent_id = parent_id
        file.type      = type
        file.content   = ""
        file.size      = len(content)
        file.is_public = 0

        code = "fail"
        error = ""
        try:
            db = xtables.get_file_table()
            if name != '':
                f = get_by_name(db, name)
                if f != None:
                    key = name
                    raise Exception(u"%s 已存在" % name)
                file_dict = dict(**file)
                del file_dict["default_value"]
                inserted_id = db.insert(**file_dict)
                update_note_content(inserted_id, content)             
                # 更新分组下面页面的数量
                update_children_count(parent_id, db = db)
                xmanager.fire("note.add", dict(name=name, type=type))
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
        key     = xutils.get_argument("key")
        value   = xutils.get_argument("value")
        db      = xtables.get_dict_table()
        item    = db.select_one(where=dict(key=key))
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

        file = db.select_one(where=dict(name=name, is_deleted=0))
        if file is not None:
            return dict(code="fail", message="%r已存在" % name)
        db.update(where=dict(id=id), name=name, mtime=xutils.format_datetime())
        event_body = dict(action="rename", id=id, name=name, type=old.type)
        xmanager.fire("note.updated", event_body)
        xmanager.fire("note.rename", event_body)
        if old.type == "group":
            cacheutil.prefix_del("group.list")
        return dict(code="success")

    def GET(self):
        return self.POST()
    
class ShareHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", type=int)
        db = xtables.get_file_table()
        db.update(is_public=1, where=dict(id=id, creator=xauth.get_current_name()))
        tag = xtables.get_file_tag_table()
        tag.update(is_public=1, where=dict(file_id=id, user=xauth.get_current_name()))
        raise web.seeother("/file/view?id=%s"%id)


class UnshareHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", type=int)
        db = xtables.get_file_table()
        db.update(is_public=0, 
            where=dict(id=id, creator=xauth.get_current_name()))
        tag = xtables.get_file_tag_table()
        tag.update(is_public=0, where=dict(file_id=id, user=xauth.get_current_name()))
        raise web.seeother("/file/view?id=%s"%id)

class FileSaveHandler:

    @xauth.login_required()
    def POST(self):
        content = xutils.get_argument("content", "")
        data    = xutils.get_argument("data", "")
        id      = xutils.get_argument("id", "0", type=int)
        type    = xutils.get_argument("type")
        version = xutils.get_argument("version", 0, type=int)
        name    = xauth.get_current_name()
        db      = xtables.get_file_table()
        where   = None
        if xauth.is_admin():
            where=dict(id=id)
        else:
            where=dict(id=id, creator=name)
        kw = dict(size=len(content), 
            mtime=xutils.format_datetime(), 
            version = version)
        if type == "html":
            kw["data"] = data
            kw["content"] = data
            if xutils.bs4 is not None:
                soup = xutils.bs4.BeautifulSoup(data, "html.parser")
                content = soup.get_text(separator=" ")
                kw["content"] = content
            kw["size"] = len(content)
        else:
            kw["content"] = content
            kw['data'] = ''
            kw["size"] = len(content)
        rowcount = update_note(db, where, **kw)
        if rowcount > 0:
            return dict(code="success")
        else:
            return dict(code="fail")

class UpdateHandler:

    @xauth.login_required()
    def POST(self):
        is_public = xutils.get_argument("public", "")
        id        = xutils.get_argument("id", type=int)
        content   = xutils.get_argument("content")
        version   = xutils.get_argument("version", type=int)
        file_type = xutils.get_argument("type")
        name      = xutils.get_argument("name", "")
        db        = xtables.get_file_table()
        file      = db.select_one(where=dict(id=id))

        assert file is not None

        # 理论上一个人是不能改另一个用户的存档，但是可以拷贝成自己的
        # 所以权限只能是创建者而不是修改者
        update_kw = dict(content=content, 
                type=file_type, 
                size=len(content),
                version=version+1);

        if name != "" and name != None:
            update_kw["name"] = name

        # 不再处理文件，由JS提交
        rowcount = update_note(db, where = dict(id=id, version=version), **update_kw)
        if rowcount > 0:
            xmanager.fire('note.updated', dict(id=id, name=name, content=content))
            raise web.seeother("/note/view?id=" + str(id))
        else:
            # 传递旧的content
            cur_version = file.version
            file.content = content
            file.version = version
            return xtemplate.render("note/view.html", 
                pathlist = [],
                file     = file, 
                content  = content, 
                error    = "更新失败, 版本冲突,当前version={},最新version={}".format(version, cur_version))

xurls = (
    r"/file/add"         , AddHandler,
    r"/note/add"         , AddHandler,
    r"/file/remove"      , RemoveHandler,
    r"/note/remove"      , RemoveHandler,
    r"/file/dict/put"    , DictPutHandler,
    r"/file/rename"      , RenameHandler,
    r"/file/share"       , ShareHandler,
    r"/file/share/cancel", UnshareHandler,
    r"/file/update"      , UpdateHandler,
    r"/note/update"      , UpdateHandler,
    r"/file/save"        , FileSaveHandler,
    r"/note/save"        , FileSaveHandler,
    r"/file/autosave"    , FileSaveHandler
)


