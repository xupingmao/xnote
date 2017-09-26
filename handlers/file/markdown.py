# encoding=utf-8
# Created by xupingmao on 2016/12
import profile

from handlers.base import *
import xauth
import xutils
import xconfig
import xtables
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

class handler(BaseHandler):

    def execute(self):
        id   = xutils.get_argument("id", "")
        name = xutils.get_argument("name", "")
        if id == "" and name == "":
            raise HTTPError(504)
        if id != "":
            id = int(id)
            file = dao.get_by_id(id)
        elif name is not None:
            file = dao.get_by_name(name)
        if file is None:
            raise web.notfound()
        
        if not file.is_public and xauth.get_current_user() is None:
            return xauth.redirect_to_login()

        dao.visit_by_id(id)
        download_csv = file.related != None and "CODE-CSV" in file.related

        user_name = xauth.get_current_name()
        can_edit = (file.creator == user_name) or (user_name == "admin")

        role = xauth.get_current_role()
        if role != "admin" and file.groups != '*' and file.groups != role:
            raise web.seeother("/unauthorized")

        self.render("file/view.html",
            file=file, 
            content = file.get_content(), 
            date2str=date2str,
            can_edit = can_edit,
            download_csv = download_csv, 
            children = [])

    def download_request(self):
        id = self.get_argument("id")
        file = dao.get_by_id(id)
        content = file.get_content()
        if content.startswith("```CSV"):
            content = content[7:-3] # remove \n
        web.ctx.headers.append(("Content-Type", 'application/octet-stream'))
        web.ctx.headers.append(("Content-Disposition", "attachment; filename=%s.csv" % quote(file.name)))
        return content

class MarkdownEdit(BaseHandler):

    @xauth.login_required()
    def default_request(self):
        id   = xutils.get_argument("id", "")
        name = xutils.get_argument("name", "")
        if id == "" and name == "":
            raise HTTPError(504)
        if id != "":
            id = int(id)
            dao.visit_by_id(id)
            file = dao.get_by_id(id)
        elif name is not None:
            file = dao.get_by_name(name)
        if file is None:
            raise web.notfound()
        download_csv = file.related != None and "CODE-CSV" in file.related
        self.render("file/markdown_edit.html", file=file, 
            content = file.get_content(), 
            date2str=date2str,
            download_csv = download_csv, 
            children = [])

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
        # groups = file.creator
        # if is_public == "on":
        #     groups = "*"
        update_kw = dict(content=content, 
                type=file_type, 
                size=len(content));

        if name != "" and name != None:
            update_kw["name"] = name

        # import pdb
        # pdb.set_trace()
        # print(upload_file)

        # 处理文件上传
        if hasattr(upload_file, "filename") and upload_file.filename != "":
            filename = upload_file.filename
            filename = filename.replace("\\", "/")
            filename = os.path.basename(filename)
            filepath, webpath = get_upload_file_path(xutils.quote(filename))
            with open(filepath, "wb") as fout:
                for chunk in upload_file.file:
                    fout.write(chunk)
            link = get_link(filename, webpath)
            update_kw["content"] = content + "\n" + link

        rowcount = dao.update(where = dict(id=id, version=version), **update_kw)
        if rowcount > 0:
            # raise web.seeother("/file/markdown/edit?id=" + str(id))
            if upload_file != None and upload_file.filename != "":
                raise web.seeother("/file/markdown/edit?id=" + str(id))
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

xurls = (
    r"/file/edit", handler, 
    r"/file/markdown", handler,
    r"/file/view", handler,
    r"/file/markdown/edit", MarkdownEdit,
    r"/file/update", UpdateHandler,
    r"/file/(\d+)/upvote", Upvote,
    r"/file/(\d+)/downvote", Downvote
)

