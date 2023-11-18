# -*- coding:utf-8 -*-  
# Created by xupingmao on 2022/09/24
# @modified 2022/04/10 18:33:45
from xnote.core import xauth, xtemplate
import xutils
from xutils import (
    fsutil,
    dbutil,
    Storage,
    webutil
)

TXT_INFO_VER = "v0.1"
_db = dbutil.get_table_v2("txt_info")

class TxtInfoDO(Storage):
    
    def __init__(self, **kw):
        self._id = 0
        self.user_id = 0
        self.user_name = ""
        self.offset = 0
        self.pagesize = 100
        self.total_size = 0
        self.file_size = 0
        self.current_offset = 0
        self.contents = []
        self.path = ""
        self.encoding = ""
        self.version = TXT_INFO_VER
        self.update(kw)

class TxtPageInfoDO(Storage):
    
    def __init__(self, **kw):
        self.offset = 0
        self.title = ""
        self.data_size = 0
        self.update(kw)

class TextHandler:

    @xauth.login_required("admin")
    def GET(self):
        method = xutils.get_argument("method", "page")
        embed = xutils.get_argument_bool("embed")

        if method == "contents":
            return self.get_bookmark()
        if method == "read_page":
            return self.read_page()
        if method == "refresh":
            return self.refresh_txt_info()
        
        kw = Storage()
        kw.embed = embed
        kw.show_right = False
        if embed:
            kw.show_nav = False
        
        return xtemplate.render("fs/page/fs_text.html", **kw)

    def get_table(self, user_name=""):
        return _db
    
    def get_txt_info_record(self, user_id=0, path=""):
        record = _db.select_first(where=dict(user_id=user_id, path=path))
        if record != None:
            return TxtInfoDO(**record)
        else:
            return None
        
    def save_txt_info(self, record:TxtInfoDO):
        assert len(record.path)>0
        if record._id == 0:
            new_id = self.get_table().insert(record)
            record._id = new_id
        else:
            self.get_table().update(record)

    def get_bookmark(self):
        path = xutils.get_argument_str("path", "")
        if path == "":
            return dict(code="400", message="path不能为空")
        
        user_info = xauth.current_user()
        assert user_info != None
        
        bookmark = self.get_txt_info_record(user_info.id, path)
        if bookmark == None:
            bookmark = TxtInfoDO()
        
        bookmark.user_name = user_info.name
        bookmark.user_id = user_info.id
        bookmark.path = path
        
        if bookmark.contents == None or bookmark.version != TXT_INFO_VER:
            bookmark = self.build_bookmark(bookmark)

        return dict(code="success", data=bookmark)
    
    def build_bookmark(self, txt_info: TxtInfoDO):
        fpath = txt_info.path
        encoding = fsutil.detect_encoding(fpath)
        contents = []
        pagesize = 5000
        total_size = 0

        if encoding == None:
            return dict(code="500", message="未知的文件编码")

        with open(fpath, encoding=encoding, errors="ignore") as fp:
            while True:
                page_info = TxtPageInfoDO()
                page_info.offset = fp.tell()
                page_data = fp.read(pagesize)
                if not page_data:
                    # None(非阻塞IO)或者长度为0的字节数组
                    break
                page_info.title = page_data[:20]
                page_info.data_size = len(page_data)
                contents.append(page_info)
                total_size += len(page_data)
        
        txt_info.contents = contents
        txt_info.pagesize = pagesize
        txt_info.version = TXT_INFO_VER
        txt_info.encoding = encoding
        txt_info.total_size = total_size
        txt_info.file_size = fsutil.get_file_size_int(fpath)
        txt_info.current_offset = 0
        
        self.save_txt_info(txt_info)
        return txt_info
    
    def read_page(self):
        user_id = xauth.current_user_id()
        offset = xutils.get_argument_int("offset", 0)
        path = xutils.get_argument_str("path", "")

        txt_info = self.get_txt_info_record(user_id, path)
        if txt_info == None:
            return dict(code="400", message="txt信息不存在,请重试")

        if offset > txt_info.file_size:
            return dict(code="500", message="没有更多内容了")

        txt_info.current_offset = offset
        self.save_txt_info(txt_info)

        with open(path, encoding=txt_info.encoding, errors="ignore") as fp:
            fp.seek(offset)
            page_data = fp.read(txt_info.pagesize)
            return dict(code="success", data=page_data)
        
    def refresh_txt_info(self):
        path = xutils.get_argument_str("path")
        user_info = xauth.current_user()
        assert user_info != None
        
        bookmark = self.get_txt_info_record(user_info.id, path)
        if bookmark == None:
            bookmark = TxtInfoDO()
        
        bookmark.user_name = user_info.name
        bookmark.user_id = user_info.id
        bookmark.path = path
        
        self.build_bookmark(bookmark)
        return webutil.SuccessResult()
    

xurls = (
    r"/fs_text", TextHandler,
)