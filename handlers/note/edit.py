# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2017
# @modified 2020/01/11 12:51:57

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
from xutils import textutil
from xtemplate import T

NOTE_DAO = xutils.DAO("note")

TYPE_MAPPING = dict(document = "md")

class NoteException(Exception):

    def __init__(self, code, message):
        super(NoteException, self).__init__(message)
        self.code = code
        self.message = message

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
    NOTE_DAO.add_history(id, version, ctx)

def get_heading_by_type(type):
    if type == "group":
        return T("创建笔记本")
    if type == "gallery":
        return T("创建相册")
    if type == "csv":
        return T("创建表格")
    return T("创建笔记")

class CreateHandler:

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
            key = time.strftime("%Y.%m.%d") + dateutil.current_wday()

        type = TYPE_MAPPING.get(type, type)

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
        note.tags       = textutil.split_words(tags)

        heading = T("创建笔记")
        code = "fail"
        error = ""
        
        try:

            if type not in ("md", "html", "csv", "gallery", "list", "group"):
                raise Exception(u"无效的类型: %s" % type)

            if name == '':
                if method == 'POST':
                    message = 'name is empty'
                    raise Exception(message)
            else:
                f = NOTE_DAO.get_by_name(name)
                if f != None:
                    key = name
                    message = u"%s 已存在" % name
                    raise Exception(message)
                inserted_id = NOTE_DAO.create(note)
                if format == "json":
                    return dict(code="success", id = inserted_id, url = "/note/edit?id=%s" % inserted_id)
                raise web.seeother("/note/edit?id={}".format(inserted_id))
        except web.HTTPError as e1:
            xutils.print_exc()
            raise e1
        except Exception as e:
            xutils.print_exc()
            error = str(e)
            if format == 'json':
                return dict(code = 'fail', message = error)

        heading = get_heading_by_type(type)

        return xtemplate.render("note/add.html", 
            show_search = False,
            heading  = heading,
            key      = "", 
            type     = type,
            name     = key, 
            tags     = tags, 
            error    = error,
            message  = error,
            groups   = NOTE_DAO.list_group(creator),
            code     = code)

    def GET(self):
        return self.POST('GET')

class AddHandler(CreateHandler):
    pass


class RemoveAjaxHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "")
        name = xutils.get_argument("name", "")
        file = None
        print("remove, id=%s, name=%s" % (id, name))

        if id != "" and id != None:
            file = NOTE_DAO.get_by_id(id)
        elif name != "":
            file = NOTE_DAO.get_by_name(name)
        else:
            return dict(code="fail", message="id,name至少一个不为空")

        if file is None:
            return dict(code="fail", message="笔记不存在")

        creator = xauth.current_name()
        if not xauth.is_admin() and file.creator != creator:
            return dict(code="fail", message="没有删除权限")

        if file.type == "group":
            children_count = NOTE_DAO.count(creator, file.id)
            if children_count > 0:
                return dict(code="fail", message="分组不为空")

        NOTE_DAO.delete(file.id)
        return dict(code="success")
        
    def POST(self):
        return self.GET()

class DictPutHandler:

    def GET(self):
        return self.POST()

    @xauth.login_required()
    def POST(self):
        # TODO 转成KV存储
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

        old = NOTE_DAO.get_by_id(id)
        if old is None:
            return dict(code="fail", message="笔记不存在")

        if old.creator != xauth.get_current_name():
            return dict(code="fail", message="没有权限")

        file = NOTE_DAO.get_by_name(name)
        if file is not None and file.is_deleted == 0:
            return dict(code="fail", message="%r已存在" % name)

        NOTE_DAO.update(id, name=name)

        event_body = dict(action="rename", id=id, name=name, type=old.type)
        xmanager.fire("note.updated", event_body)
        xmanager.fire("note.rename", event_body)
        return dict(code="success")

    def GET(self):
        return self.POST()
    
class ShareHandler:

    @xauth.login_required()
    def GET(self):
        id      = xutils.get_argument("id")
        note    = check_get_note(id)
        NOTE_DAO.update(id, is_public = 1)
        raise web.seeother("/note/view?id=%s"%id)


class UnshareHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        note = check_get_note(id)
        NOTE_DAO.update(id, is_public = 0)
        raise web.seeother("/note/view?id=%s"%id)

def check_get_note(id):
    if xauth.is_admin():
        note = NOTE_DAO.get_by_id(id)
    else:
        note = NOTE_DAO.get_by_id_creator(id, xauth.current_name())

    if note is None:
        raise NoteException("404", "笔记不存在")
    return note

def update_and_notify(file, update_kw):
    rowcount = NOTE_DAO.update(file.id, **update_kw)
    if rowcount > 0:
        xmanager.fire('note.updated', dict(
            id = file.id, 
            name = file.name, 
            mtime = dateutil.format_datetime(),
            content = update_kw.get("content"), 
            version = file.version + 1))
    else:
        # 更新冲突了
        raise NoteException("409", "更新失败")

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

        try:
            file = check_get_note(id)
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

            update_and_notify(file, kw)
            return dict(code = "success")
        except NoteException as e:
            return dict(code = "fail", message = e.message)

class UpdateHandler:

    @xauth.login_required()
    def POST(self):
        is_public = xutils.get_argument("public", "")
        id        = xutils.get_argument("id")
        content   = xutils.get_argument("content")
        version   = xutils.get_argument("version", 0, type=int)
        file_type = xutils.get_argument("type")
        name      = xutils.get_argument("name", "")

        try:
            file = check_get_note(id)

            # 理论上一个人是不能改另一个用户的存档，但是可以拷贝成自己的
            # 所以权限只能是创建者而不是修改者
            update_kw = dict(content=content, 
                    type = file_type, 
                    size = len(content),
                    version = version);
            if name != "" and name != None:
                update_kw["name"] = name
            # 更新并且发出消息
            update_and_notify(file, update_kw)
            raise web.seeother("/note/%s" % id)
        except NoteException as e:
            return xtemplate.render("note/view.html", 
                pathlist = [],
                file     = file, 
                content  = content, 
                error    = e.message)

class StickHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        note = check_get_note(id)
        NOTE_DAO.update(id, priority = 1)
        raise web.found("/note/%s" % id)

class UnstickHandler:
    
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        note = check_get_note(id)
        NOTE_DAO.update(id, priority = 0)
        raise web.found("/note/%s" % id)

class ArchiveHandler:

    def GET(self):
        id = xutils.get_argument("id")
        note = check_get_note(id)
        NOTE_DAO.update(id, archived=True)
        raise web.found("/note/%s" % id)

class UnarchiveHandler:

    def GET(self):
        id = xutils.get_argument("id")
        note = check_get_note(id)
        NOTE_DAO.update(id, archived=False)
        raise web.found("/note/%s" % id)

class MoveHandler:
    
    @xauth.login_required()
    def GET(self):
        id        = xutils.get_argument("id", "")
        parent_id = xutils.get_argument("parent_id", "")
        file = NOTE_DAO.get_by_id_creator(id, xauth.current_name())
        if file is None:
            return dict(code="fail", message="笔记不存在")
        if str(id) == str(parent_id):
            return dict(code="fail", message="不能移动到自身目录")

        NOTE_DAO.move(file, parent_id)
        return dict(code="success")

    def POST(self):
        return self.GET()

class AppendAjaxHandler:

    def GET(self):
        return self.POST()

    @xauth.login_required()
    def POST(self):
        user    = xauth.current_name()
        note_id = xutils.get_argument("note_id")
        content = xutils.get_argument("content")
        version = xutils.get_argument("version", 1, type = int)
        note = NOTE_DAO.get_by_id(note_id)

        if note == None:
            return dict(code = "404", message = "note not found")

        if note.creator != user:
            return dict(code = "403", message = "unauthorized")

        if note.list_items is None:
            note.list_items = []
        note.list_items.append(content)
        NOTE_DAO.update0(note)
        xmanager.fire('note.updated', dict(id=note_id, 
            name = note.name, 
            mtime = dateutil.format_datetime(), 
            content = content, version=version+1))
        return dict(code = "success")
        

xurls = (
    r"/note/add"         , AddHandler,
    r"/note/create"      , CreateHandler,
    r"/note/remove"      , RemoveAjaxHandler,
    r"/note/rename"      , RenameAjaxHandler,
    r"/note/update"      , UpdateHandler,
    r"/note/share"       , ShareHandler,
    r"/note/save"        , SaveAjaxHandler,
    r"/note/append"      , AppendAjaxHandler,
    r"/note/share/cancel", UnshareHandler,
    r"/note/stick"       , StickHandler,
    r"/note/unstick"     , UnstickHandler,
    r"/note/archive"     , ArchiveHandler,
    r"/note/unarchive"   , UnarchiveHandler,
    r"/note/move"        , MoveHandler,
    r"/note/group/move"  , MoveHandler,

    r"/file/dict/put"    , DictPutHandler,
    r"/file/share"       , ShareHandler,
    r"/file/share/cancel", UnshareHandler,
    r"/file/save"        , SaveAjaxHandler,
    r"/file/autosave"    , SaveAjaxHandler
)


