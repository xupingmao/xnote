# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2017
# @modified 2022/04/04 20:47:41

"""笔记编辑相关处理"""
from handlers.note.dao_category import refresh_category_count
import web
import time
from xnote.core import xauth
import xutils
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.core import xconfig
from xutils import Storage
from xutils import dateutil
from xutils import cacheutil
from xutils import dbutil
from xutils import textutil
from xutils import webutil
from xnote.core.xtemplate import T
from .constant import *
from . import dao_delete
from .dao_api import NoteDao
from . import dao as note_dao
from . import dao_delete
from . import dao_share

from handlers.note import dao_read
from handlers.note import dao_draft

NOTE_DAO = xutils.DAO("note")

DEFAULT_CREATE_TEMPLATE = "note/page/create.html"

# 编辑锁有效期
EDIT_LOCK_EXPIRE = 600

class NoteException(Exception):

    def __init__(self, code, message):
        super(NoteException, self).__init__(message)
        self.code = code
        self.message = message

def get_heading_by_type(type):
    title = u"创建" + NOTE_TYPE_DICT.get(type, u"笔记")
    return T(title)

def fire_update_event(note_old):
    """
    @param {note} note_old 旧版本的笔记
    """
    note = NoteDao.get_by_id(note_old.id)
    if note is None:
        return
    event_body = dict(id=note.id, 
            name = note.name, 
            mtime = dateutil.format_datetime(), 
            content = note.content, 
            version = note.version)
    xmanager.fire("note.updated", event_body)
    xmanager.fire("note.update", event_body)

def fire_rename_event(note):
    event_body = dict(action = "rename", id = note.id, name = note.name, type = note.type)
    xmanager.fire("note.rename", event_body)

def create_log_func(note, ctx):
    method   = ctx.method
    date_str: str = ctx.date

    if method != "POST":
        # GET请求直接返回
        return

    if date_str is None or date_str == "":
        date_str = time.strftime("%Y-%m-%d")
    note.name = u"日志:" + date_str + dateutil.convert_date_to_wday(date_str)
    return note_dao.create_note(note, date_str)

def default_create_func(note, ctx):
    method   = ctx.method
    date_str = ctx.date
    name     = note.name

    if method != "POST":
        # GET请求直接返回
        return

    if name == '':
        message = u'标题为空'
        raise Exception(message)

    return note_dao.create_note(note, date_str)

CREATE_FUNC_DICT = {
    "log.bak": create_log_func
}

def list_groups_for_create(creator):
    notes = note_dao.list_group(creator, orderby = "name")

    sticky_groups   = list(filter(lambda x: x.priority != None and x.priority > 0, notes))
    archived_groups = list(filter(lambda x: x.archived == True, notes))
    normal_groups   = list(filter(lambda x: x not in sticky_groups and x not in archived_groups, notes))

    groups = []

    for item in sticky_groups:
        item.name = u"[置顶]" + item.name
        groups.append(item)

    for item in normal_groups:
        groups.append(item)

    for item in archived_groups:
        item.name = u"[归档]" + item.name
        groups.append(item)

    return groups

class CreateHandler:

    @xauth.login_required()
    def POST(self, method='POST'):
        name = xutils.get_argument_str("name")
        tags      = xutils.get_argument_str("tags", "")
        key       = xutils.get_argument_str("key", "")
        content   = xutils.get_argument_str("content", "")
        type0     = xutils.get_argument_str("type", "md")
        date      = xutils.get_argument("date", "")
        format    = xutils.get_argument_str("_format", "")
        parent_id = xutils.get_argument_int("parent_id")
        deafult_name = xutils.get_argument_str("default_name")

        user_info = xauth.current_user()
        assert user_info != None
        creator = user_info.name
        creator_id = user_info.id

        xmanager.add_visit_log(creator, "/note/create")

        if key == "":
            key = time.strftime("%Y.%m.%d") + dateutil.current_wday()

        if name == "":
            name = deafult_name

        type = NOTE_TYPE_MAPPING.get(type0, type0)

        note = note_dao.NoteDO()
        note.name = name
        note.creator   = creator
        note.creator_id = creator_id
        note.parent_id = parent_id
        note.type      = type
        note.type0 = type0 # 原始输入的type
        note.content   = content
        note.data      = ""
        note.size      = len(content)
        note.is_public = 0
        note.priority  = 0
        note.version   = 0
        note.is_deleted = 0
        note.tags = tags.split()
        note.level = 0

        if note.parent_id < 0:
            note.archived = True
            note.priority = -1
            note.level = -1

        heading = T("创建笔记")
        code = "fail"
        error = ""
        ctx = Storage(method = method, date = date, creator_id=creator_id)
        
        try:
            self.check_before_create(note)

            create_func = CREATE_FUNC_DICT.get(type, default_create_func)
            inserted_id = create_func(note, ctx)

            new_note = note_dao.get_by_id_creator(inserted_id, creator)
            self.after_create(new_note)

            if type == "group":
                redirect_url = "/note/view?id=%s" % inserted_id
            else:
                redirect_url = "/note/edit?id=%s" % inserted_id

            if format == "json":
                return dict(code="success", id = inserted_id, url = redirect_url)

            if inserted_id != None:
                raise web.seeother(redirect_url)

        except web.HTTPError as e1:
            xutils.print_exc()
            raise e1
        except Exception as e:
            xutils.print_exc()
            error = xutils.u(e)
            if format == 'json':
                return dict(code = 'fail', message = error)

        heading  = get_heading_by_type(type)
        template = DEFAULT_CREATE_TEMPLATE

        return xtemplate.render(template, 
            show_search = False,
            heading  = heading,
            type     = type,
            name     = name, 
            tags     = tags, 
            error    = error,
            message  = error,
            NOTE_TYPE_LIST = NOTE_TYPE_LIST,
            groups   = list_groups_for_create(creator),
            code     = code)

    def GET(self):
        return self.POST('GET')
    

    def check_before_create(self, note):
        type = note.type
        if type not in VALID_NOTE_TYPE_SET:
            raise Exception(u"无效的类型: %s" % note.type0)

        name = note.name
        check_by_name = note_dao.get_by_name(note.creator, name)
        if check_by_name != None:
            message = u"笔记【%s】已存在" % name
            raise Exception(message)
        
        if note.type != "group":
            if note.parent_id in ("", "0"):
                message = u"请选择归属的笔记本"
                raise Exception(message)

    def after_create(self, created_note):
        if created_note == None:
            return
        if created_note.type == "group":
            refresh_category_count(created_note.creator, created_note.category)


class RemoveAjaxHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id")
        name = xutils.get_argument_str("name")
        file = None

        if id != "" and id != None:
            file = note_dao.get_by_id(id)
        elif name != "":
            file = note_dao.get_by_name(xauth.current_name(), name)
        else:
            return webutil.FailedResult(code="fail", message="id,name至少一个不为空")

        if file is None:
            return webutil.FailedResult(code="fail", message="笔记不存在")

        creator = xauth.current_name()
        if not xauth.is_admin() and file.creator != creator:
            return dict(code="fail", message="没有删除权限")

        if file.type == "group":
            children_count = note_dao.count_by_parent(creator, file.id)
            if children_count > 0:
                return dict(code="fail", message="分组不为空")

        dao_delete.delete_note(file.id)
        
        self.after_delete(file)

        return webutil.SuccessResult()
        
    def POST(self):
        return self.GET()
    
    def after_delete(self, note):
        if note.type == "group":
            refresh_category_count(note.creator, note.category)


class RecoverAjaxHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "")
        name = xutils.get_argument("name", "")
        file = None

        if id != "" and id != None:
            file = note_dao.get_by_id(id)
        elif name != "":
            file = note_dao.get_by_name(xauth.current_name(), name)
        else:
            return dict(code="fail", message="id,name至少一个不为空")

        if file is None:
            return dict(code="fail", message="笔记不存在")

        creator = xauth.current_name()
        if not xauth.is_admin() and file.creator != creator:
            return dict(code="fail", message="没有恢复权限")

        dao_delete.recover_note(id)
        
        self.after_recover(file)

        return dict(code="success")
        
    def POST(self):
        return self.GET()
    
    def after_recover(self, note):
        if note.type == "group":
            refresh_category_count(note.creator, note.category)



class RenameAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id   = xutils.get_argument("id")
        name = xutils.get_argument("name")
        if name == "" or name is None:
            return dict(code="fail", message="名称为空")
        
        assert isinstance(id, str), "无效的ID"

        old = NoteDao.get_by_id(id)
        if old is None:
            return dict(code="fail", message="笔记不存在")

        if old.creator != xauth.get_current_name():
            return dict(code="fail", message="没有权限")

        file = note_dao.get_by_name(xauth.current_name(), name)
        if file is not None:
            return dict(code="fail", message="%r已存在" % name)

        with dbutil.get_write_lock(id):
            new_file = Storage(**old)
            new_file.name = name
            new_file.mtime = dateutil.format_datetime()

            update_and_notify(old, new_file)

        fire_rename_event(old)
        return dict(code="success")

    def GET(self):
        return self.POST()
    

class NoteShareHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id")
        note_info = check_get_note(id)
        
        share_info = note_dao.ShareInfoDO()
        share_info.share_type=note_dao.ShareTypeEnum.note_public.value
        share_info.target_id = id
        share_info.from_id = note_info.creator_id
        note_dao.ShareInfoDao.insert_ignore(share_info)
        note_dao.update_note(id, is_public = 1)

        return webutil.SuccessResult()

    @xauth.login_required()
    def POST(self):
        id   = xutils.get_argument("id")
        share_to = xutils.get_argument("share_to")
        note = check_get_note(id)

        if not xauth.is_user_exist(share_to):
            return dict(code = "fail", message = "用户[%s]不存在" % share_to)

        share_from = xauth.current_name()
        if share_to == share_from:
            return dict(code = "fail", message = "不需要分享给自己")

        dao_share.share_note_to(note.id, share_from, share_to)
        return dict(code = "success", message = "分享成功")

class LinkShareHandler:

    @xauth.login_required()
    def POST(self):
        id   = xutils.get_argument("id")
        note = check_get_note(id)
        if note.token != None and note.token != "":
            return webutil.SuccessResult(data = "/note/view?token=%s" % note.token)
        else:
            token = note_dao.create_token("note", note.id)
            note_dao.update_note(note.id, token = token)
        return webutil.SuccessResult(data = "/note/view?token=%s" % token)

class UnshareHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id")
        to_user = xutils.get_argument_str("share_to", "")
        try:
            note = check_get_note(id)
            if to_user != "":
                dao_share.delete_share(id, to_user = to_user)
            else:
                note_dao.update_note(id, is_public = 0)
                note_dao.ShareInfoDao.delete_by_target(share_type="note_public", target_id=id)
            return webutil.SuccessResult(message = "取消分享成功")
        except Exception as e:
            return webutil.FailedResult(message=str(e))

    def POST(self):
        return self.GET()

def check_get_note(id):
    if id == "" or id == 0:
        raise NoteException("400", "笔记ID为空")

    note = NoteDao.get_by_id(id)

    if note is None:
        raise NoteException("404", "笔记不存在")

    user_info = xauth.current_user()
    assert user_info != None

    if note.creator != user_info.name:
        raise NoteException("403", "无权编辑")

    note.creator_id = user_info.id
    return note

def update_and_notify(file, update_kw):
    """更新内容并且广播消息"""
    edit_token = update_kw.get("edit_token", "")
    if edit_token != None and edit_token != "":
        # 这里只加一个0秒的锁，相当于更新完之后锁就释放了
        if not dao_draft.refresh_edit_lock(file.id, edit_token, time.time()):
            raise NoteException("conflict", "当前笔记正在被其他设备编辑")

    # 先记录变更历史
    note_dao.add_history(file.id, update_kw.get("version"), update_kw)

    # 执行变更
    rowcount = note_dao.update_note(file.id, **update_kw)
    if rowcount > 0:
        dao_draft.save_draft(file.id, "") # 清空草稿
        fire_update_event(file)
    else:
        # 更新冲突了
        raise NoteException("409", "更新失败")

class SaveAjaxHandler:

    @xauth.login_required()
    def POST(self):
        try:
            return self.do_post()
        except NoteException as e:
            return webutil.FailedResult(code = "fail", message = e.message)

    
    def do_post(self):
        content = xutils.get_argument_str("content", "")
        data = xutils.get_argument_str("data", "")
        id = xutils.get_argument_int("id")
        type = xutils.get_argument_str("type")
        version = xutils.get_argument_int("version", 0)
        edit_token = xutils.get_argument_str("edit_token", "")

        with dbutil.get_write_lock(id):
            file = check_get_note(id)
            if version != file.version:
                raise NoteException("conflict", "笔记已经被修改，请刷新后重试")
            
            new_file = Storage(**file)
            new_file.size = len(content)
            new_file.mtime = xutils.format_datetime()
            new_file.version = version+1
            new_file.edit_token = edit_token

            if type == "html":
                new_file.data = data
                new_file.content = data
                if xutils.bs4 is not None:
                    soup = xutils.bs4.BeautifulSoup(data, "html.parser")
                    content = soup.get_text(separator=" ")
                    new_file.content = content
                new_file.size = len(content)
            else:
                new_file.content = content
                new_file.data = ""
                new_file.size = len(content)

            update_and_notify(file, new_file)
            return webutil.SuccessResult()


class UpdateHandler:

    @xauth.login_required()
    def POST(self):
        try:
            return self.do_post()
        except NoteException as e:
            return dict(code = "fail", message = e.message)
    
    def do_post(self):
        is_public = xutils.get_argument("public", "")
        id        = xutils.get_argument("id", "")
        content   = xutils.get_argument("content", "")
        version   = xutils.get_argument("version", 0, type=int)
        file_type = xutils.get_argument("type")
        name      = xutils.get_argument("name", "")
        resp_type = xutils.get_argument("resp_type", "html")
        edit_token = xutils.get_argument("edit_token", "")

        file = None

        assert isinstance(id, str)
        assert isinstance(version, int)
        assert isinstance(content, str)

        with dbutil.get_write_lock(id):
            file = check_get_note(id)
            if version != file.version:
                raise NoteException("fail", "笔记已经被修改，请刷新后重试")

            # 理论上一个人是不能改另一个用户的存档，但是可以拷贝成自己的
            # 所以权限只能是创建者而不是修改者
            file_new = Storage(**file)
            file_new.content = content
            file_new.type = file_type
            file_new.size = len(content)
            file_new.version = version + 1
            file_new.edit_token = edit_token
            file_new.mtime = dateutil.format_datetime()

            if name != "" and name != None:
                file_new["name"] = name
            # 更新并且发出消息
            update_and_notify(file, file_new)

            if resp_type == "json":
                return dict(code = "success")

            raise web.seeother(file.url)


class StickHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id")
        level = xutils.get_argument_int("level", 1)
        # 正常(0), 归档(-1), 置顶(1)
        assert level in (-1,0,1)

        note = check_get_note(id)
        note_dao.NoteIndexDao.update_level(note_id=int(id), level = level)
        raise web.found("/note/%s" % id)

class UnstickHandler:
    
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id")
        note = check_get_note(id)
        note_dao.NoteIndexDao.update_level(note_id=id, level = 0)
        raise web.found("/note/%s" % id)

class ArchiveHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        note = check_get_note(id)
        note_dao.update_note(id, archived=True, priority = -1)
        raise web.found("/note/%s" % id)

class ResetHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        note = check_get_note(id)
        note_dao.update_note(id, archived=False, priority = 0)
        raise web.found(note.url)

class UnarchiveHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        note = check_get_note(id)
        note_dao.update_note(id, archived=False, priority = 0)
        raise web.found("/note/%s" % id)

class UpdateStatusHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_int("id")
        status = xutils.get_argument_int("status")
        if status not in (0, -1, 1):
            return webutil.FailedResult(code="fail", message="无效的状态: %s" % status)
        note = check_get_note(id)
        note_dao.NoteIndexDao.update_level(id, level = status)
        return webutil.SuccessResult(message = "更新状态成功")

class UpdateOrderByHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        orderby = xutils.get_argument("orderby")
        if orderby not in note_dao.ORDER_BY_SET:
            return webutil.FailedResult(code = "fail", message = "无效的排序方式: %s" % orderby)
        note = check_get_note(id)
        
        note_dao.update_note(id, orderby = orderby, creator_id = note.creator_id)
        return webutil.SuccessResult(message = "更新排序方式成功")

class MoveAjaxHandler:
    
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id")
        parent_id = xutils.get_argument_int("parent_id")

        user_name = xauth.current_name_str()
        file = note_dao.get_by_id_creator(id, user_name)
        target_book = note_dao.get_by_id_creator(parent_id, user_name)

        if file is None:
            return webutil.FailedResult(code="fail", message="笔记不存在")
        
        if target_book is None:
            return webutil.FailedResult(code="fail", message="目标笔记本不存在")
        
        if str(id) == parent_id:
            return webutil.FailedResult(code="fail", message="不能移动到自身目录")
        
        if target_book.type != "group":
            return webutil.FailedResult(code="fail", message="只能移动到笔记本中")

        pathlist = note_dao.list_path(target_book)
        for item in pathlist:
            if item.id == file.id:
                return dict(code="fail", message="不能移动笔记本到自身的子笔记本中")
        
        if file.type == "group":
            max_depth = xconfig.get_system_config("max_book_depth", 2)
            assert isinstance(max_depth, int)

            # pathlist包含了根目录
            depth = len(pathlist) - 1 + dao_read.get_note_depth(file)
            if depth > max_depth:
                return webutil.FailedResult(code="fail", message="笔记本的层次不能超过%d, 当前层次:%d" % (max_depth, depth))

        with dbutil.get_write_lock(user_name):
            note_dao.move_note(file, parent_id)
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

        note_id = str(note_id)
        note = NoteDao.get_by_id(note_id)

        if note == None:
            return dict(code = "404", message = "note not found")

        if note.creator != user:
            return dict(code = "403", message = "unauthorized")

        if note.list_items is None:
            note.list_items = []
        note.list_items.append(content)
        note_dao.update0(note)

        fire_update_event(note)
        return dict(code = "success")

class TouchHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        resp_type = xutils.get_argument("resp_type", "")
        user_name = xauth.current_name()
        # TODO 创建一个watch日志记录即可
        note = NoteDao.get_by_id_creator(id, user_name)
        if note != None:
            kw = Storage()
            kw.version = note.version+1
            kw.name = note.name
            kw.mtime = xutils.format_datetime()
            update_and_notify(note, kw)
        
        if resp_type == "json":
            return dict(code="success")

        raise web.found(note.url)
    
    def POST(self):
        return self.GET()

class DraftHandler:
    """保存草稿功能"""

    @xauth.login_required()
    def POST(self):
        action = xutils.get_argument_str("action")
        note_id = xutils.get_argument_str("id", "")
        content = xutils.get_argument_str("content")
        token   = xutils.get_argument_str("token")
        version = xutils.get_argument_int("version", 0)

        note = check_get_note(note_id)
        if action == "lock_and_save":
            with dbutil.get_write_lock(note_id):
                if not dao_draft.refresh_edit_lock(note_id, token, time.time() + EDIT_LOCK_EXPIRE):
                    return dict(code = "conflict", message = "该文章正在被其他设备编辑，是否偷锁编辑")
                
                if version < note.version:
                    return dict(code = "version_too_low", message = "当前编辑的版本过低，是否加载最新的草稿")

                dao_draft.save_draft(note_id, content)
                return dict(code = "success")
        if action == "steal_lock":
            dao_draft.steal_edit_lock(note_id, token, time.time() + EDIT_LOCK_EXPIRE)
            draft_content = dao_draft.get_draft(note_id)
            if draft_content == None or draft_content == "":
                draft_content = note.content
            return dict(code = "success", data = draft_content)

        return dict(code = "biz.error", message = "未知的action:%s" % action)

class UpdateAttrAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id", "")
        key = xutils.get_argument("key", "")
        value = xutils.get_argument("value", "")
        assert isinstance(key, str)

        if id == "":
            return dict(code="400", message="id不能为空")

        if key == "":
            return dict(code="400", message="key不能为空")
        
        user_name = xauth.current_name()
        note_info = NoteDao.get_by_id_creator(id, user_name)

        if note_info == None:
            return dict(code="400", message="笔记不存在")
        
        if key in ("category"):
            old_value = getattr(note_info, key)
            setattr(note_info, key, value)
            note_dao.update0(note_info)
            if key == "category":
                refresh_category_count(user_name, value)
                refresh_category_count(user_name, old_value)
            return dict(code="success")
        else:
            return dict(code="400", message="不支持的属性")


class CopyHandler:

    def GET(self):
        pass

    @xauth.login_required()
    def POST(self):
        name = xutils.get_argument_str("name", "")
        origin_id = xutils.get_argument_int("origin_id")
        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name
        user_id = user_info.id

        origin_note = NoteDao.get_by_id_creator(origin_id, user_name)
        if origin_note == None:
            return webutil.FailedResult(code="404", message = "笔记不存在或没有权限")
        
        new_note_dict = note_dao.NoteDO()
        new_note_dict.name = name
        new_note_dict.content = origin_note.content
        new_note_dict.type = origin_note.type
        new_note_dict.parent_id = origin_note.parent_id
        new_note_dict.creator = user_name
        new_note_dict.creator_id = user_id

        try:
            new_note_id = NoteDao.create(new_note_dict)
            return dict(code="success", url = NoteDao.get_view_url_by_id(new_note_id))
        except Exception as e:
            return webutil.FailedResult(code="500", message = str(e))


xurls = (
    r"/note/add"         , CreateHandler,
    r"/note/create"      , CreateHandler,
    r"/note/remove"      , RemoveAjaxHandler,
    r"/note/rename"      , RenameAjaxHandler,
    r"/note/recover"     , RecoverAjaxHandler,
    r"/note/update"      , UpdateHandler,
    r"/note/save"        , SaveAjaxHandler,
    r"/note/draft"       , DraftHandler,
    r"/note/attribute/update", UpdateAttrAjaxHandler,
    r"/note/copy", CopyHandler,

    r"/note/append"      , AppendAjaxHandler,
    r"/note/stick"       , StickHandler,
    r"/note/archive"     , ArchiveHandler,
    r"/note/reset"       , ResetHandler,
    r"/note/move"        , MoveAjaxHandler,
    r"/note/group/move"  , MoveAjaxHandler,

    r"/note/unstick"     , UnstickHandler,
    r"/note/unarchive"   , UnarchiveHandler,
    r"/note/touch"       , TouchHandler,
    r"/note/status"      , UpdateStatusHandler,
    r"/note/orderby"     , UpdateOrderByHandler,
    
    # 分享
    r"/note/share",        NoteShareHandler,
    r"/note/share/public", NoteShareHandler,
    r"/note/share/cancel", UnshareHandler,
    r"/note/link_share",   LinkShareHandler,

    # 不建议使用的
    r"/file/save"        , SaveAjaxHandler,
    r"/file/autosave"    , SaveAjaxHandler,
)


