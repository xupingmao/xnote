#coding:utf-8
from BaseHandler import *
from FileDB import *
from tornado.escape import *
import math
import os
import json
import base64
from config import *
from urllib.parse import quote

import xutils


DIR_NAME = WORKING_DIR

def Result(success = True, msg=None):
    return {"success": success, "result": None, "msg": msg}

def getFileBasePath():
    return FILE_BASE

def getDbPath():
    return os.path.join(FILE_BASE, "index.db")
        
def to_json(obj):
    if obj is None:
        return None
    if isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = to_json(obj[i])
        return obj
    return obj.__dict__

def json_encode_obj(obj):
    return json_encode(to_json(obj))

def date2str(d):
    ct = time.gmtime(d / 1000)
    return time.strftime('%Y-%m-%d %H:%M:%S', ct)
    
class WebFile:
    def __init__(self, name, path):
        self.path = path
        self.name = name

def getFiles(webpath):
    curpath = '';
    files = [WebFile('home', '/')]
    for item in webpath.split('/'):
        if item == '': continue
        curpath += '/' + item
        file = WebFile(item, curpath)
        files.append(file)
    return files
    

class LinkHandler(BaseHandler):
        
    def get(self):
        name = self.get_argument("name", None)
        if name is not None:
            self.redirect("/file?option=search&key=" + name)
        else:
            self.redirect("/")

def updateContent(id, content, user_name=None, type=None):
    if user_name is None:
        sql = "update file set content = %s,size=%s, smtime='%s'" \
            % (to_sqlite_obj(content), len(content), dateutil.format_time())
    else:
        # 这个字段还在考虑中是否添加
        # 理论上一个人是不能改另一个用户的存档，但是可以拷贝成自己的
        sql = "update file set content = %s,size=%s,smtime='%s',modifier='%s"\
            % (to_sqlite_obj(content), len(content), dateutil.format_time(), user_name)
    if type:
        sql += ", type='%s'" % type
    sql += " where id=%s" % id

    xutils.db_execute("db/data.db", sql)

    
class FileHandler(BaseHandler):
    
    def get(self):
        self._service = FileService.instance()
        BaseHandler.get(self)
        
    def post(self):
        self.get()
        
    def writeRequest(self):
        pass
        
    def find(self):
        service = self._service
        id = self.get_argument("id", None)
        name = self.get_argument("name", None)
        key = self.get_argument("key", None)
        r = Result()
        if id is not None:
            file = service.getById(int(id))
            r['result'] = to_json(file)
        elif name is not None:
            file = service.getByName(name)
            r['result'] = to_json(file)
        elif key is not None:
            files = service.search(key)
            r['result'] = to_json(files)
        else:
            r['success'] = False
        self.write(json_encode(r))
        
    # chr(65292),    
    def addRequest(self):
        name = self.get_argument("name", "")
        tags = self.get_argument("tags", "")
        key  = self.get_argument("key", "")

        file = FileDO(name)
        file.atime = dateutil.get_seconds()
        file.satime = dateutil.format_time()
        file.mtime = dateutil.get_seconds()
        file.smtime = dateutil.format_time()
        file.ctime = dateutil.get_seconds()
        file.sctime = dateutil.format_time()
        error = ""
        try:
            if name != '':
                self._service.insert(file)
                raise web.seeother("/file/edit?name=%s" % quote(name))
        except Exception as e:
            error = e
        self.render("file-add.html", key = "", name = key, tags = tags, error=error)
        
    def repairRequest(self):
        name = self.get_argument("name")
        file = self._service.getByName(name)
        file.fixRelated()
        file = self._service.getByName(name)
        self.write(json_encode_obj(file))
        
    def fixPathRequest(self):
        id = self.get_argument("id")
        file = self._service.getById(int(id))
        if file.path[0] == '/':
            file.path = file.path[1:]
            self._service.update(file)
        raise web.seeother("/file")
        
    def delRequest(self):
        id = self.get_argument("id")
        file = self._service.getById(id)
        self._service.delById(id)
        # raise web.seeother("/file/edit?id=" + str(file.parent_id))
        raise web.seeother("/file/recent_edit")
        
    def updateRequest(self):
        id = self.get_argument("id")
        key = self.get_argument("key")
        value = self.get_argument("value")
        r = Result()
        try:
            self._service.updateField(id, key, value)
            self.write(json_encode(r))
        except Exception as e:
            r = ErrorResult(e)
            self.write(json_encode(r))
            
    def updateRelatedRequest(self):
        id = self.get_argument("id")
        value = self.get_argument("value")
        value = value.upper()
        r = Result()
        try:
            self._service.updateField(id, "related", value)
            self.write(json_encode(r))
        except Exception as e:
            r = ErrorResult(e)
            self.write(json_encode(r))
            
    def updateContentRequest(self):
        id = self.get_argument("id")
        content = self.get_argument("content")
        file = self._service.getById(int(id))
        assert file is not None
        updateContent(id, content)
        raise web.seeother("/file/edit?id=" + id)
        
        
    def listRequest(self):
        page = self.get_argument("page", None)
        if page is None:
            list = self._service.getAll()
            page = 1
        else:
            list = self._service.getAll(int(page)-1)
        count = self._service.count()
        # 1..20 -> 1
        # 21..40 -> 2
        pages = math.ceil(int(count) / 20);
        self.render("file-list.html", files = list, key = "", count=count, pages=pages, page=int(page))
        
    def rank_request(self):
        order = self.get_argument("order", None)
        if order == "order":
            files = self._service.get_last(50)
        else:
            files = self._service.get_top(20)
        self.render("file-list.html", files = files, key="")
        
    def recentRequest(self):
        count = self.get_argument("count", 20)
        files = self._service.getRecent(count)
        self.render("file-list.html", files = files, key = "")
        
    def reorder_request(self):
        files = self._service.forget()
        self.redirect("/file?option=management")

    def renameRequest(self):
        fileId = self.get_argument("fileId")
        newName = self.get_argument("newName")
        record = self._service.getByName(newName)
        old_record = self._service.getById(fileId)
        if old_record is None:
            return Result(False, "file with ID %s do not exists" % fileId)
        elif record is not None:
            return Result(False, "file %s already exists!" % repr(newName))
        else:
            old_name = old_record.name
            old_name_upper = old_name.upper()
            new_name_upper = newName.upper()
            if old_name_upper not in old_record.related and new_name_upper not in old_record.related:
                old_record.related += "," + newName
            else:
                old_record.related = old_record.related.replace(old_name_upper, new_name_upper);
            old_record.name = newName
            self._service.update(old_record, "name", "related", "smtime")
            return Result(True)

    def defaultRequest(self):
        return self.recentRequest()
        
    def openDirectoryRequest(self):
        name = self.get_argument("path", None)
        if name is None:
            path = self.get_argument("webpath")
            name = netutil.get_path(WEBDIR, path)
            # print(WEBDIR, name)
            # name = os.path.join(WEBDIR, path)
        if os.path.isdir(name):
            fsutil.openDirectory(name)
            ret = { "success": True}
        else:
            ret = {"success": False, "errorMsg": "%s is not a dirname" % name}

        return ret

    def console_request(self):
        self.render("file-console.html")

    # def upload_request(self):
    #     fsutil.check_create_dirs(UPLOAD_DIR)
    #     file_meta_list = self.request.files['file']
    #     # upload_type = self.get_argument("upload_type", None)
    #     for meta in file_meta_list:
    #         filename = meta['filename']
    #         filepath = os.path.join(UPLOAD_DIR, filename)
    #         with open(filepath, "wb") as up:
    #             up.write(meta['body'])
    #         raise web.seeother("/tool#/tools/upload/")
    #     return raise web.seeother("/tool")

    def upload_request(self):
        x = web.input(file = {})
        if 'file' in x:
            fsutil.check_create_dirs(UPLOAD_DIR)
            filepath = os.path.join(UPLOAD_DIR, x.file.filename)
            fout = open(filepath, "wb")
            # fout.write(x.file.file.read())
            for chunk in x.file.file:
                fout.write(chunk)
            fout.close()
        raise web.seeother("/tool?path=/static/upload")



    def management_request(self):
        self.render("file-management.html")

    def deleted_list_request(self):
        self.render("file-list.html", files = self._service.get_deleted_list())

    def physically_delete_request(self):
        id = self.get_argument("id")
        self._service.physically_delete(id)
        raise web.seeother("/file?option=deleted_list")
        
    def recent_modified_request(self):
        s_days = self.get_argument("days")
        days = int(s_days)
        self.render("file-list.html", files=self._service.get_recent_modified(days))

    def recent_created_request(self):
        s_days = self.get_argument("days")
        days = int(s_days)
        self.render("file-list.html", files=self._service.get_recent_created(days))

    def db_struct_request(self):
        file_struct = FileService.instance().getTableDefine("file")
        self.render("db-struct.html", file_struct = file_struct)
        
handler = FileHandler