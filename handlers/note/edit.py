# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2017
# @modified 2019/06/13 01:32:20

"""笔记编辑相关处理"""
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
from xutils import dbutil
from xtemplate import T

def get_by_name(db, name):
    return db.select_first(where=dict(name = name, 
        is_deleted = 0, 
        creator = xauth.get_current_name()))

def update_children_count(parent_id, db=None):
    if parent_id is None or parent_id == "":
        return
    if db is None:
        db = get_file_db()
    group_count = db.count(where="parent_id=$parent_id AND is_deleted=0", 
        vars=dict(parent_id=parent_id))
    db.update(size=group_count, where=dict(id=parent_id))

def update_note_content(id, content, data=''):
    if id is None:
        return
    if content is None:
        content = ''
    if data is None:
        data = ''
    db = xtables.get_note_content_table()
    result = db.select_first(where=dict(id=id))
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
    kw["atime"] = dateutil.format_time()
    # 处理乐观锁
    version = where.get("version")
    if version != None:
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

@xmanager.listen(["note.add", "note.updated", "note.rename", "note.remove"])
def update_note_cache(ctx):
    type = ctx.get("type", "")
    cacheutil.prefix_del("[%s]note" % xauth.get_current_name())

@xmanager.listen("note.updated")
def record_history(ctx):
    id      = ctx.get("id")
    content = ctx.get("content")
    version = ctx.get("version")
    mtime   = ctx.get("mtime")
    name    = ctx.get("name")
    xutils.call("note.add_history", id, version, ctx)

class AddHandler:

    @xauth.login_required()
    def POST(self, method='POST'):
        name      = xutils.get_argument("name", "")
        tags      = xutils.get_argument("tags", "")
        key       = xutils.get_argument("key", "")
        content   = xutils.get_argument("content", "")
        type      = xutils.get_argument("type", "md")
        format    = xutils.get_argument("_format", "")
        parent_id = xutils.get_argument("parent_id", "0")

        if key == "":
            key = time.strftime("%Y.%m.%d")

        creator        = xauth.current_name()
        note           = Storage(name = name)
        note.atime     = xutils.format_datetime()
        note.mtime     = xutils.format_datetime()
        note.ctime     = xutils.format_datetime()
        note.creator   = creator
        note.parent_id = parent_id
        note.type      = type
        note.content   = content
        note.data      = ""
        note.size      = len(content)
        note.is_public = 0
        note.priority  = 0
        note.version   = 0
        note.is_deleted = 0

        code = "fail"
        error = ""
        try:
            if name == '':
                if method == 'POST':
                    message = 'name is empty'
                    raise Exception(message)
            else:
                f = xutils.call("note.get_by_name", name)
                if f != None:
                    key = name
                    message = u"%s 已存在" % name
                    raise Exception(message)
                inserted_id = xutils.call("note.create", note)

                # 更新分组下面页面的数量 TODO
                # update_children_count(parent_id, db = db)
                xmanager.fire("note.add", dict(name=name, type=type))

                # 创建对应的文件夹
                if type != "group":
                    dirname = os.path.join(xconfig.UPLOAD_DIR, creator, str(parent_id), str(inserted_id))
                else:
                    dirname = os.path.join(xconfig.UPLOAD_DIR, creator, str(inserted_id))
                xutils.makedirs(dirname)

                if format == "json":
                    return dict(code="success", id=inserted_id)
                raise web.seeother("/note/view?id={}".format(inserted_id))
        except web.HTTPError as e1:
            xutils.print_exc()
            raise e1
        except Exception as e:
            xutils.print_exc()
            error = str(e)
            if format == 'json':
                return dict(code = 'fail', message = error)
        return xtemplate.render("note/add.html", 
            show_aside = True,
            key      = "", 
            type     = type,
            name     = key, 
            tags     = tags, 
            error    = error,
            pathlist = [Storage(name=T("New_Note"), url="/note/add")],
            message  = error,
            groups   = xutils.call("note.list_group"),
            code     = code)

    def GET(self):
        return self.POST('GET')

class RemoveAjaxHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "")
        name = xutils.get_argument("name", "")
        file = None

        print("remove", id, name)

        if id == "" and name == "":
            return dict(code="fail", message="id,name至少一个不为空")

        if id != "":
            file = xutils.call("note.get_by_id", id)
        elif name != "":
            file = xutils.call("note.get_by_name", name)
        if file is None:
            return dict(code="fail", message="文件不存在")

        creator = xauth.current_name()
        if not xauth.is_admin() and file.creator != creator:
            return dict(code="fail", message="没有删除权限")

        if file.type == "group":
            children_count = xutils.call("note.count", creator, file.id)
            if children_count > 0:
                return dict(code="fail", message="分组不为空")

        xutils.call("note.delete", id)
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
        item    = db.select_first(where=dict(key=key))
        current = xutils.format_datetime()
        if key == "" or key is None:
            return dict(code="fail", message="key is empty")
        if item is None:
            db.insert(key=key, value=value, ctime = current, mtime = current)
        else:
            db.update(value = value, mtime = current, where = dict(key=key))
        return db.select_first(where=dict(key=key))

class RenameAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id   = xutils.get_argument("id")
        name = xutils.get_argument("name")
        if name == "" or name is None:
            return dict(code="fail", message="名称为空")

        old = xutils.call("note.get_by_id", id)
        if old is None:
            return dict(code="fail", message="笔记不存在")

        if old.creator != xauth.get_current_name():
            return dict(code="fail", message="没有权限")

        file = xutils.call("note.get_by_name", name)
        if file is not None and file.is_deleted == 0:
            return dict(code="fail", message="%r已存在" % name)

        xutils.call("note.update", dict(id=id), name=name)

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
        id      = xutils.get_argument("id")
        creator = xauth.current_name()
        xutils.call("note.update", dict(id = id, creator = creator), is_public = 1)
        raise web.seeother("/note/view?id=%s"%id)


class UnshareHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        creator = xauth.current_name()
        xutils.call("note.update", dict(id = id, creator = creator), is_public = 0)
        raise web.seeother("/note/view?id=%s"%id)

class SaveAjaxHandler:

    @xauth.login_required()
    def POST(self):
        content = xutils.get_argument("content", "")
        data    = xutils.get_argument("data", "")
        id      = xutils.get_argument("id")
        type    = xutils.get_argument("type")
        version = xutils.get_argument("version", 0, type=int)
        name    = xauth.get_current_name()
        where   = None

        if xauth.is_admin():
            where = dict(id=id)
        else:
            where = dict(id=id, creator=name)
        kw = dict(size = len(content), 
            mtime = xutils.format_datetime(), 
            version = version + 1)
        if type == "html":
            kw["data"]    = data
            kw["content"] = data
            if xutils.bs4 is not None:
                soup          = xutils.bs4.BeautifulSoup(data, "html.parser")
                content       = soup.get_text(separator=" ")
                kw["content"] = content
            kw["size"] = len(content)
        else:
            kw["content"] = content
            kw['data']    = ''
            kw["size"]    = len(content)
        rowcount = xutils.call("note.update", where, **kw)
        if rowcount > 0:
            xmanager.fire('note.updated', dict(id=id, name=name, 
                mtime = dateutil.format_datetime(),
                content = content, version=version+1))
            return dict(code="success")
        else:
            return dict(code="fail", message="更新失败")

class UpdateHandler:

    @xauth.login_required()
    def POST(self):
        is_public = xutils.get_argument("public", "")
        id        = xutils.get_argument("id")
        content   = xutils.get_argument("content")
        version   = xutils.get_argument("version", 0, type=int)
        file_type = xutils.get_argument("type")
        name      = xutils.get_argument("name", "")
        db        = xtables.get_file_table()
        file      = xutils.call("note.get_by_id", id)

        if file is None:
            return xtemplate.render("note/view.html", 
                pathlist = [],
                file     = file, 
                content  = content, 
                error    = "笔记不存在")

        # 理论上一个人是不能改另一个用户的存档，但是可以拷贝成自己的
        # 所以权限只能是创建者而不是修改者
        update_kw = dict(content=content, 
                type = file_type, 
                size = len(content),
                version = version);

        if name != "" and name != None:
            update_kw["name"] = name

        # 不再处理文件，由JS提交
        rowcount = xutils.call("note.update", where = dict(id=id, version=version), **update_kw)
        if rowcount > 0:
            xmanager.fire('note.updated', dict(id=id, name=file.name, 
                mtime = dateutil.format_datetime(),
                content = content, version=version+1))
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

class StickHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        user = xauth.current_name()
        xutils.call("note.update", dict(id = id, creator = user), priority = 1)
        raise web.found("/note/view?id=" + str(id))

class UnstickHandler:
    
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        user = xauth.current_name()
        xutils.call("note.update", dict(id = id, creator = user), priority = 0)
        raise web.found("/note/view?id=" + str(id))

xurls = (
    r"/note/add"         , AddHandler,
    r"/note/remove"      , RemoveAjaxHandler,
    r"/note/rename"      , RenameAjaxHandler,
    r"/note/update"      , UpdateHandler,
    r"/note/share"       , ShareHandler,
    r"/note/save"        , SaveAjaxHandler,
    r"/note/share/cancel", UnshareHandler,
    r"/note/stick"       , StickHandler,
    r"/note/unstick"     , UnstickHandler,

    r"/file/dict/put"    , DictPutHandler,
    r"/file/share"       , ShareHandler,
    r"/file/share/cancel", UnshareHandler,
    r"/file/save"        , SaveAjaxHandler,
    r"/file/autosave"    , SaveAjaxHandler
)


