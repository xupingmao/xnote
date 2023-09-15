# -*- coding:utf-8 -*-  
# Created by xupingmao on 2022/09/24
# @modified 2022/04/10 18:33:45
import xauth
import xtemplate
import xutils
from xutils import (
    fsutil,
    dbutil,
    Storage
)

TXT_INFO_VER = "v0.1"
_db = dbutil.get_hash_table("txt_info")

class TextHandler:

    @xauth.login_required("admin")
    def GET(self):
        method = xutils.get_argument("method", "page")
        embed = xutils.get_argument_bool("embed")

        if method == "contents":
            return self.get_bookmark()
        if method == "read_page":
            return self.read_page()
        
        kw = Storage()
        kw.embed = embed
        kw.show_right = False
        if embed:
            kw.show_nav = False
        
        return xtemplate.render("fs/page/fs_text.html", **kw)

    def get_table(self, user_name):
        assert len(user_name) > 0
        return _db.sub_table(user_name)

    def get_bookmark(self):
        path = xutils.get_argument("path", "")
        if path == "":
            return dict(code="400", message="path不能为空")
        
        user_name = xauth.current_name()
        db = self.get_table(user_name)
        bookmark = db.get(path)
        if bookmark == None or bookmark.contents == None or bookmark.version != TXT_INFO_VER:
            bookmark = self.build_bookmark(user_name, path)

        return dict(code="success", data=bookmark)
    
    def build_bookmark(self, user_name, fpath):
        encoding = fsutil.detect_encoding(fpath)
        contents = []
        pagesize = 5000
        total_size = 0

        if encoding == None:
            return dict(code="500", message="未知的文件编码")

        with open(fpath, encoding=encoding, errors="ignore") as fp:
            while True:
                page_info = Storage()
                page_info.offset = fp.tell()
                page_data = fp.read(pagesize)
                if not page_data:
                    # None(非阻塞IO)或者长度为0的字节数组
                    break
                page_info.title = page_data[:20]
                page_info.data_size = len(page_data)
                contents.append(page_info)
                total_size += len(page_data)
        
        txt_info = Storage()
        txt_info.contents = contents
        txt_info.path = fpath
        txt_info.pagesize = pagesize
        txt_info.version = TXT_INFO_VER
        txt_info.encoding = encoding
        txt_info.total_size = total_size
        txt_info.file_size = fsutil.get_file_size_int(fpath)
        txt_info.current_offset = 0

        db = self.get_table(user_name)
        db.put(fpath, txt_info)
        return txt_info
    
    def read_page(self):
        user_name = xauth.current_name()
        offset = xutils.get_argument_int("offset", 0)
        path = xutils.get_argument_str("path", "")

        db = self.get_table(user_name)
        txt_info = db.get(path)
        if txt_info == None:
            return dict(code="400", message="txt信息不存在,请重试")

        if offset > txt_info.file_size:
            return dict(code="500", message="没有更多内容了")

        txt_info.current_offset = offset
        db.put(path, txt_info)

        with open(path, encoding=txt_info.encoding, errors="ignore") as fp:
            fp.seek(offset)
            page_data = fp.read(txt_info.pagesize)
            return dict(code="success", data=page_data)

xurls = (
    r"/fs_text", TextHandler,
)