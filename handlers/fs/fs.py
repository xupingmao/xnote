# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# 

"""文件服务
- 目录
- 大文件下载
"""
import os
import mimetypes
import time
import web
import xutils
import xauth
from handlers.base import *
from xutils import FileItem


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
    kw["os"]            = os
    kw["is_stared"]     = is_stared
    kw["search_type"]   = "fs"
    kw["get_file_size"] = get_file_size
    return kw

def get_parent_path(path):
    path2 = path.replace("\\", "/")
    if path2.endswith("/"):
        path2 = path[:-1]
    if not path.endswith("/"):
        path = path+"/"
    return os.path.dirname(path2).replace("\\", "/") # fix windows file sep

def list_abs_dir(path):
    # pathlist = []
    # for item in os.listdir(path):
    #     pathlist.append(os.path.join(path, item))
    return [os.path.join(path, item) for item in os.listdir(path)]

def getpathlist2(path):
    if not path.endswith("/"):
        path += "/"
    pathsplit = path.split("/")
    pathlist = []
    for i in range(len(pathsplit)):
        path = "/".join(pathsplit[:i])
        if "" != os.path.basename(path):
            # pathlist.append(path)
            pathlist.append(FileItem(path))
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
        filelist = []
        for item in drives_list:
            if item.endswith("\\"):
                item = item[:-1]
            filelist.append(item)
        return filelist
    except Exception as e:
        return ["C:"]
    else:
        pass
    finally:
        pass

class FileSystemHandler:

    mime_types = {
        ""     : 'application/octet-stream', # Default
        '.jpg' : 'image/jpeg',
        '.png' : 'image/png',
        '.gif' : 'image/gif',
        '.webp': 'image/webp',
        '.mp4' : 'video/mp4',
        '.avi' : 'video/avi',
        '.html': 'text/html; charset=utf-8',
        '.py'  : 'text/plain; charset=utf-8',
        '.sh'  : 'text/plain; charset=utf-8',
        '.txt' : 'text/plain; charset=utf-8',
        '.md'  : 'text/plain; charset=utf-8',
        '.ini' : 'text/plain; charset=utf-8',
    }

    encodings = {
        # 二进制传输的编码格式
    }

    def handle_content_type(self, path):
        """Content-Type设置, 优先级从高到低依次是：自定义配置、系统配置、默认配置"""
        path = xutils.decode_name(path)
        name, ext = os.path.splitext(path)
        mime_type = self.mime_types.get(ext.lower())
        if mime_type is None:
            mime_type, mime_encoding = mimetypes.guess_type(path)
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
            if xutils.is_windows() and path == "/":
                # return self.list_win_drives()
                filelist = get_win_drives()
            else:
                filelist = list_abs_dir(path)
        except OSError:
            return "No permission to list directory"

        # filelist中路径均不带/
        # 排序：文件夹优先，按字母顺序排列
        # filelist.sort(key=lambda a: a.lower())
        # filelist.sort(key=lambda a: not os.path.isdir(os.path.join(path,a)))
        filelist = [FileItem(item) for item in filelist]
        filelist.sort()

        # SAE上遇到中文出错
        # Fix bad filenames，修改不生效
        # filelist = list(map(lambda x: xutils.decode_bytes(x.encode("utf-8", errors='surrogateescape')), filelist))

        # Fix, some `file` in *nix is not file either directory. os.stat方法报错
        path = path.replace("\\", "/")
        kw   = get_filesystem_kw()
        kw["filelist"]     = filelist
        kw["path"]         = path
        kw["fspathlist"]   = xutils.splitpath(path)
        
        return xtemplate.render("fs/fs.html", **kw)

    def list_root(self):
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

                xutils.trace("<== Content-Range:%s" % content_range)
                # 发送数据
                fp = open(path, "rb")
                try:
                    fp.seek(range_start)
                    rest = range_end - range_start + 1
                    readsize = min(rest, blocksize)
                    while readsize > 0:
                        # print("%s send %s K" % (time.ctime(), readsize))
                        yield fp.read(readsize)
                        rest -= readsize
                        readsize = min(rest, blocksize)
                finally:
                    # 基本上和with等价，这里打印出来
                    xutils.trace("close %s" % path)
                    fp.close()
            except Exception as e:
                # 其他未知异常
                xutils.print_stacktrace()
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
                # print("%s Read %s K" % (time.ctime(), blocksize))
                yield block
                block = fp.read(blocksize)

    def read_file(self, path):
        environ = web.ctx.environ
        etag = '"%s"' % os.path.getmtime(path)
        client_etag = environ.get('HTTP_IF_NONE_MATCH')
        web.header("Etag", etag)

        self.handle_content_type(path)
        # self.handle_content_encoding(ext)

        if etag == client_etag:
            web.ctx.status = "304 Not Modified"
            return b'' # 其实webpy已经通过yield空bytes来避免None
        else:
            http_range = environ.get("HTTP_RANGE")
            blocksize = 64 * 1024;
            # print_env()

            if http_range is not None:
                xutils.trace("==> HTTP_RANGE {}", http_range)
                return self.read_range(path, http_range, blocksize)
            else:
                return self.read_all(path, blocksize)            

    def handle_get(self, path):
        # TODO SAE上有编码错误
        # print("Load Path:", path)
        if path == "":
            return self.list_root()
        if os.path.isdir(path):
            return self.list_directory(path)
        elif os.path.isfile(path):
            return self.read_file(path)
        else:
            return "Not Readable %s" % path

    @xauth.login_required("admin")
    def GET(self, path):
        if not os.path.exists(path):
            # /fs/ 文件名来源是文件系统提供的，尝试unquote不会出现问题
            path = xutils.unquote(path)
        return self.handle_get(path)
        

class StaticFileHandler(FileSystemHandler):
    allowed_prefix = ["static", "img", "app", "files", "tmp", "scripts"]

    def is_path_allowed(self, path):
        for prefix in self.allowed_prefix:
            if path.startswith(prefix):
                return True
        return False

    """外置数据的静态文件支持"""
    def GET(self, path):
        # path = xutils.unquote(path)
        if not self.is_path_allowed(path):
            xauth.check_login("admin")
        data_prefix = config.DATA_DIR
        if not path.startswith("static"):
            newpath = os.path.join(data_prefix, path)
        else:
            newpath = path
            # 兼容static目录数据
            if not os.path.exists(newpath):
                # len("static/") = 7
                newpath = os.path.join(data_prefix, newpath[7:])
        path = newpath
        if not os.path.isfile(path):
            # 静态文件不允许访问文件夹
            web.ctx.status = "404 Not Found"
            return "Not Readable %s" % path
        return self.handle_get(path)

class AddDirHandler:

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument("path", "")
        dirname = xutils.get_argument("dirname", "")
        if path == "":
            return dict(code="fail", message="path is empty")
        dirname = xutils.quote_unicode(dirname)
        newpath = os.path.join(path, dirname)
        try:
            os.makedirs(newpath)
            return dict(code="success")
        except Exception as e:
            xutils.print_stacktrace()
            return dict(code="fail", message=str(e))


name = "文件系统"
description = "下载和上传文件"

xurls = (
    r"/fs-", handler, 
    r"/fs/add_dir", AddDirHandler,
    r"/fs/(.*)", FileSystemHandler,
    r"/(static/.*)", StaticFileHandler,
    r"/data/(.*)", StaticFileHandler,
    r"/(app/.*)", StaticFileHandler,
    r"/(tmp/.*)", StaticFileHandler
)


