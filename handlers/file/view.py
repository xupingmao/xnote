# encoding=utf-8
# Created by xupingmao on 2016/12
import profile
import math
import re

from handlers.base import *
import xauth
import xutils
import xconfig
import xtables
import xtemplate
import xmanager
from web import HTTPError
from . import dao

config = xconfig

def date2str(d):
    ct = time.gmtime(d / 1000)
    return time.strftime('%Y-%m-%d %H:%M:%S', ct)


def try_decode(bytes):
    try:
        return bytes.decode("utf-8")
    except:
        return bytes.decode("gbk")

class ViewHandler:

    def GET(self, op):
        id   = xutils.get_argument("id", "")
        name = xutils.get_argument("name", "")
        page = xutils.get_argument("page", 1, type=int)
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        db   = xtables.get_file_table()
        user_name = xauth.get_current_name()

        if id == "" and name == "":
            raise HTTPError(504)
        if id != "":
            id = int(id)
            file = dao.get_by_id(id, db=db)
        elif name is not None:
            file = dao.get_by_name(name, db=db)
        if file is None:
            raise web.notfound()
        
        if not file.is_public and user_name != "admin" and user_name != file.creator:
            raise web.seeother("/unauthorized")
        show_search_div = False
        pathlist = dao.get_pathlist(db, file)
        can_edit = (file.creator == user_name) or (user_name == "admin")
        role = xauth.get_current_role()

        # 定义一些变量
        files = []
        amount = 0
        template_name = "file/view.html"

        if file.type == "group":
            amount = db.count(where="parent_id=$id AND is_deleted=0 AND creator=$creator", 
                vars=dict(id=file.id, creator=user_name))
            files = db.select(where=dict(parent_id=file.id, is_deleted=0, creator=user_name), 
                order="priority DESC, mtime DESC", 
                limit=pagesize, 
                offset=(page-1)*pagesize)
            content = file.get_content()
            show_search_div = True
        elif file.type == "md" or file.type == "text":
            dao.visit_by_id(id, db)
            content = file.get_content()
            if op == "edit":
                template_name = "file/markdown_edit.html"
        else:
            content = file.content
            content = content.replace(u'\xad', '\n')
            content = content.replace(u'\n', '<br/>')
            file.data = file.data.replace(u"\xad", "\n")
            file.data = file.data.replace(u'\n', '<br/>')
            if file.data == None or file.data == "":
                file.data = content
            dao.visit_by_id(id, db)
        
        return xtemplate.render(template_name,
            file=file, 
            op=op,
            date2str=date2str,
            can_edit = can_edit,
            pathlist = pathlist,
            page_max = math.ceil(amount/pagesize),
            show_search_div = show_search_div,
            page = page,
            page_url = "/file/view?id=%s&page=" % id,
            files = files)

def sqlite_escape(text):
    if text is None:
        return "NULL"
    if not (isinstance(text, str)):
        return repr(text)
    # text = text.replace('\\', '\\')
    text = text.replace("'", "''")
    return "'" + text + "'"

def result(success = True, msg=None):
    return {"success": success, "result": None, "msg": msg}

def is_img(filename):
    name, ext = os.path.splitext(filename)
    return ext.lower() in (".gif", ".png", ".jpg", ".jpeg", ".bmp")

def get_link(filename, webpath):
    if is_img(filename):
        return "![%s](%s)" % (filename, webpath)
    return "[%s](%s)" % (filename, webpath)

class UpdateHandler(BaseHandler):

    @xauth.login_required()
    def default_request(self):
        is_public = xutils.get_argument("public", "")
        id        = xutils.get_argument("id", type=int)
        content   = xutils.get_argument("content")
        version   = xutils.get_argument("version", type=int)
        file_type = xutils.get_argument("type")
        name      = xutils.get_argument("name", "")
        upload_file  = xutils.get_argument("file", {})

        file = dao.get_by_id(id)
        assert file is not None

        # 理论上一个人是不能改另一个用户的存档，但是可以拷贝成自己的
        # 所以权限只能是创建者而不是修改者
        update_kw = dict(content=content, 
                type=file_type, 
                size=len(content));

        if name != "" and name != None:
            update_kw["name"] = name

        # 不再处理文件，由JS提交
        rowcount = dao.update(where = dict(id=id, version=version), **update_kw)
        if rowcount > 0:
            if upload_file != None and upload_file.filename != "":
                raise web.seeother("/file/view?id=" + str(id))
            else:
                raise web.seeother("/file/view?id=" + str(id))
        else:
            # 传递旧的content
            cur_version = file.version
            file.content = content
            file.version = version
            return self.render("file/view.html", file=file, 
                content = content, 
                date2str=date2str,
                children = [],
                error = "更新失败, version冲突,当前version={},最新version={}".format(version, cur_version))

    def rename_request(self):
        fileId = self.get_argument("fileId")
        newName = self.get_argument("newName")
        record = dao.get_by_name(newName)

        fileId = int(fileId)
        old_record = dao.get_by_id(fileId)

        if old_record is None:
            return result(False, "file with ID %s do not exists" % fileId)
        elif record is not None:
            return result(False, "file %s already exists!" % repr(newName))
        else:
            # 修改名称不用乐观锁
            rowcount = dao.update(where= dict(id = fileId), name = newName)
            return result(rowcount > 0)

    def del_request(self):
        id = int(self.get_argument("id"))
        dao.update(where=dict(id=id), is_deleted=1)
        raise web.seeother("/file/recent_edit")

class Upvote:

    @xauth.login_required()
    def GET(self, id):
        id = int(id)
        db = xtables.get_file_table()
        file = db.select_one(where=dict(id=int(id)))
        db.update(priority=1, where=dict(id=id))
        raise web.seeother("/file/view?id=%s" % id)

class Downvote:
    @xauth.login_required()
    def GET(self, id):
        id = int(id)
        db = xtables.get_file_table()
        file = db.select_one(where=dict(id=int(id)))
        db.update(priority=0, where=dict(id=id))
        raise web.seeother("/file/view?id=%s" % id)

class RenameHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        name = xutils.get_argument("name")
        if name == "" or name is None:
            return dict(code="fail", message="名称为空")
        db = xtables.get_file_table()
        file = db.select_one(where=dict(name=name))
        if file is not None:
            return dict(code="fail", message="%r已存在" % name)
        db.update(where=dict(id=id), name=name)
        return dict(code="success")

    def GET(self):
        return self.POST()

class FileSaveHandler:

    @xauth.login_required()
    def POST(self):
        content = xutils.get_argument("content", "")
        data    = xutils.get_argument("data", "")
        id = xutils.get_argument("id", "0", type=int)
        type = xutils.get_argument("type")
        name = xauth.get_current_name()
        db = xtables.get_file_table()
        where = None
        if xauth.is_admin():
            where=dict(id=id)
        else:
            where=dict(id=id, creator=name)
        kw = dict(size=len(content), mtime=xutils.format_datetime(), 
            where=where)
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
            kw["size"] = len(content)
        rowcount = db.update(**kw)
        if rowcount > 0:
            return dict(code="success")
        else:
            return dict(code="fail")

class MarkHandler:

    def GET(self):
        id = xutils.get_argument("id")
        db = xtables.get_file_table()
        db.update(is_marked=1, where=dict(id=id))
        raise web.seeother("/file/view?id=%s"%id)

class UnmarkHandler:
    def GET(self):
        id = xutils.get_argument("id")
        db = xtables.get_file_table()
        db.update(is_marked=0, where=dict(id=id))
        raise web.seeother("/file/view?id=%s"%id)
        
class LibraryHandler:

    def GET(self):
        return xtemplate.render("file/library.html")

xurls = (
    r"/file/(edit|view)", ViewHandler, 
    r"/file/rename", RenameHandler,
    r"/file/update", UpdateHandler,
    r"/file/save", FileSaveHandler,
    r"/file/autosave", FileSaveHandler,
    r"/file/(\d+)/upvote", Upvote,
    r"/file/(\d+)/downvote", Downvote,
    r"/file/mark", MarkHandler,
    r"/file/unmark", UnmarkHandler,
    
    r"/file/markdown", ViewHandler,
    r"/file/library", LibraryHandler
)

