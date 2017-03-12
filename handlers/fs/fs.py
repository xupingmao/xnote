# encoding=utf-8

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

class FileSystemHandler:

    mime_types = {
        ""    : 'application/octet-stream', # Default
        '.jpg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.mp4': 'video/mp4',
        '.avi': 'video/avi',
        '.html': 'text/html',
        '.py' : 'text/plain',
    }

    def list_directory(self, path):
        try:
            list = os.listdir(path)
        except OSError:
            return "No permission to list directory"
        list.sort(key=lambda a: a.lower())
        # Fix, some `file` in *nix is not file either directory.
        list.sort(key=lambda a: not os.path.isdir(os.path.join(path,a)))

        path2 = path.replace("\\", "/")
        if path2.endswith("/"):
            path2 = path[:-1]
        if not path.endswith("/"):
            path = path+"/"
        parent_path = os.path.dirname(path2).replace("\\", "/") # fix windows file sep
        path = path.replace("\\", "/")
        kw = get_filesystem_kw()
        kw["filelist"] = list
        kw["path"] = path
        kw["fspathlist"] = getpathlist(path)
        kw["current_path"] = path
        kw["parent_path"] = parent_path
        kw["get_file_size"] = get_file_size

        # handle home
        home = path.split("/")[0]
        if home[-1] != '/':
            home+='/'
        kw["home"] = home
        return xtemplate.render("fs/fs.html", **kw)

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
        mime_type = self.mime_types.get(ext.lower())
        if mime_type is None:
            mime_type = self.mime_types['']

        web.header("Content-Type", mime_type)

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


    def GET(self, path):
        path = xutils.unquote(path)
        # TODO 有编码错误
        # print("Load Path:", path)
        user = xauth.get_current_user()
        if user is None or user["name"] != "admin":
            web.status = "404 No permission"
            return "No permission"
        if os.path.isdir(path):
            return self.list_directory(path)
        elif os.path.isfile(path):
            return self.read_file(path)
        else:
            return "Not Readable %s" % path

name = "文件系统"
description = "下载和上传文件"

xurls = (r"/fs-", handler, r"/fs/(.*)", FileSystemHandler)