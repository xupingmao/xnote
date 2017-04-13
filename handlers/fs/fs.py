# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# 

"""文件服务
- 目录
- 大文件下载
"""
import os

import web
from handlers.base import *
import xutils
import xauth

class handler(BaseHandler):

    __url__ = r"/fs-"

    def execute(self):
        if xutils.is_windows():
            raise web.seeother("/fs-D:/")
        else:
            raise web.seeother("/fs-/")

def is_stared(path):
    return config.has_config("STARED_DIRS", path)

def get_file_size(filepath):
    try:
        st = os.stat(filepath)
        if st and st.st_size > 0:
            return xutils.get_pretty_file_size(None, size=st.st_size)
        return "-"
    except OSError as e:
        return "-"

def get_filesystem_kw():
    """return filesystem utils"""
    kw = {}
    kw["os"] = os
    kw["is_stared"] = is_stared
    kw["search_type"] = "fs"
    return kw

def getpathlist(path):
    if not path.endswith("/"):
        path += "/"
    pathsplit = path.split("/")
    pathlist = []
    for i in range(len(pathsplit)):
        path = "/".join(pathsplit[:i])
        if "" != os.path.basename(path):
            pathlist.append(path)
    return pathlist

def print_env():
    for key in web.ctx.env:
        print(" - - %-20s = %s" % (key, web.ctx.env.get(key)))


def get_win_drives():
    """获取Windows系统的驱动器列表"""
    try:
        import ctypes
        import sys
        lp_buf = ctypes.create_string_buffer(100)
        ctypes.windll.kernel32.GetLogicalDriveStringsA(ctypes.sizeof(lp_buf), lp_buf)
        drives_str = lp_buf.raw.decode(sys.getdefaultencoding())
        drives_list = drives_str.split("\x00")
        drives_list = list(filter(lambda x:len(x) > 0, drives_list))
        return drives_list
    except Exception as e:
        raise
    else:
        pass
    finally:
        pass

class FileSystemHandler:

    mime_types = {
        ""    : 'application/octet-stream', # Default
        '.jpg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.mp4': 'video/mp4',
        '.avi': 'video/avi',
        '.html': 'text/html; charset=utf-8',
        '.py' : 'text/plain; charset=utf-8',
        '.txt': 'text/plain; charset=utf-8',
    }

    encodings = {
        # 二进制传输的编码格式
    }

    def handle_content_type(self, ext):
        """Content-Type设置"""
        mime_type = self.mime_types.get(ext.lower())
        if mime_type is None:
            mime_type = self.mime_types['']

        web.header("Content-Type", mime_type)

    def handle_content_encoding(self, ext):
        """Content-Encoding设置，这里应该是二进制编码格式
        """
        if ext in self.encodings:
            web.header("Content-Encoding", self.encodings[ext])

    def list_directory(self, path):
        try:
            filelist = os.listdir(path)
        except OSError:
            return "No permission to list directory"
        filelist.sort(key=lambda a: a.lower())

        # Fix bad filenames
        filelist = list(map(lambda x: xutils.decode_bytes(x.encode("utf-8", errors='surrogateescape')), filelist))

        # Fix, some `file` in *nix is not file either directory.
        filelist.sort(key=lambda a: not os.path.isdir(os.path.join(path,a)))

        path2 = path.replace("\\", "/")
        if path2.endswith("/"):
            path2 = path[:-1]
        if not path.endswith("/"):
            path = path+"/"
        parent_path = os.path.dirname(path2).replace("\\", "/") # fix windows file sep
        path = path.replace("\\", "/")
        kw = get_filesystem_kw()
        kw["filelist"] = filelist
        kw["path"] = path
        kw["fspathlist"] = getpathlist(path)
        kw["current_path"] = path
        kw["parent_path"] = parent_path
        kw["get_file_size"] = get_file_size

        # handle home
        if path[0] != "/":
            home = path.split("/")[0]
            if home[-1] != '/':
                home+='/'
        else:
            # 类Unix系统
            home = "/"
        kw["home"] = home
        return xtemplate.render("fs/fs.html", **kw)

    def list_root(self):
        if xutils.is_windows():
            raise web.seeother("/fs/C:/")
        else:
            raise web.seeother("/fs//")

    def read_range(self, path, http_range, blocksize):
        range_list = http_range.split("bytes=")
        if len(range_list) == 2:
            # 包含完整的范围
            range_list = range_list[1]
            try:
                range_start, range_end = range_list.split('-')
                range_start = int(range_start)
                total_size = os.stat(path).st_size
                if range_end != "":
                    range_end = int(range_end)
                else:
                    range_end  = total_size-1
                    web.header("Content-Length", total_size)

                content_range = "bytes %s-%s/%s" % (range_start, range_end, total_size)
                # 设置HTTP响应状态
                web.ctx.status = "206 Partial Content"
                # 发送HTTP首部
                web.header("Accept-Ranges", "bytes")
                web.header("Content-Range", content_range)

                print(" <== Content-Range:%s" % content_range)
                
                # 发送数据
                with open(path, "rb") as fp:
                    fp.seek(range_start)
                    rest = range_end - range_start + 1
                    readsize = min(rest, blocksize)
                    while readsize > 0:
                        yield fp.read(readsize)
                        rest -= readsize
                        readsize = min(rest, blocksize)
            except Exception as e:
                # yield最好不要和return混用
                yield self.read_all(path, blocksize)
        else:
            # 处理不了，返回所有的数据
            yield self.read_all(path, blocksize)

    def read_all(self, path, blocksize):
        total_size = os.stat(path).st_size
        web.header("Content-Length", total_size)
        with open(path, "rb") as fp:
            block = fp.read(blocksize)
            while block:
                yield block
                block = fp.read(blocksize)

    def read_file(self, path):
        environ = web.ctx.environ
        etag = '"%s"' % os.path.getmtime(path)
        client_etag = environ.get('HTTP_IF_NONE_MATCH')
        web.header("Etag", etag)

        name, ext = os.path.splitext(path)
        self.handle_content_type(ext)
        # self.handle_content_encoding(ext)

        if etag == client_etag:
            web.ctx.status = "304 Not Modified"
            return b'' # 其实webpy已经通过yield空bytes来避免None
        else:
            http_range = environ.get("HTTP_RANGE")
            print(" ==> HTTP_RANGE", http_range)
            blocksize = 64 * 1024;
            # print_env()

            if http_range is not None:
                return self.read_range(path, http_range, blocksize)
            else:
                return self.read_all(path, blocksize)            


    @xauth.login_required("admin")
    def GET(self, path):
        path = xutils.unquote(path)
        # TODO 有编码错误
        # print("Load Path:", path)
        if path == "":
            return self.list_root()
        if os.path.isdir(path):
            return self.list_directory(path)
        elif os.path.isfile(path):
            return self.read_file(path)
        else:
            return "Not Readable %s" % path

name = "文件系统"
description = "下载和上传文件"

xurls = (r"/fs-", handler, r"/fs/(.*)", FileSystemHandler)