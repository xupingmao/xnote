# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# @modified 2020/01/26 20:05:29

"""xnote文件服务，主要功能:
1. 静态文件服务器，生产模式使用强制缓存，开发模式使用协商缓存
2. 文件浏览器
3. 文件下载，支持断点续传
4. 文件上传
"""
import os
import mimetypes
import time
import web
import xutils
import xauth
import xconfig
import xtemplate
import shutil
import xmanager
from xutils import FileItem, u, Storage, fsutil

def is_stared(path):
    return xconfig.has_config("STARED_DIRS", path)

def get_file_size(filepath):
    return fsutil.get_file_size(filepath, format=True)

def get_filesystem_kw():
    """return filesystem utils"""
    kw = {}
    kw["os"]            = os
    kw["search_type"]   = "fs"
    kw["get_file_size"] = get_file_size
    kw["html_title"]    = "文件"
    # kw["show_aside"]    = False
    return kw

def get_parent_path(path):
    path2 = path.replace("\\", "/")
    if path2.endswith("/"):
        path2 = path[:-1]
    if not path.endswith("/"):
        path = path+"/"
    return os.path.dirname(path2).replace("\\", "/") # fix windows file sep

def list_abs_dir(path):
    return [os.path.join(path, item) for item in os.listdir(path)]

def print_env():
    for key in web.ctx.env:
        print(" - - %-20s = %s" % (key, web.ctx.env.get(key)))


def list_win_drives():
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

def check_file_auth(path, user_name):
    user_dir = os.path.join(xconfig.UPLOAD_DIR, user_name)
    path = os.path.abspath(path)
    return path.startswith(user_dir)

def process_file_list(pathlist, parent = None):
    filelist = [FileItem(fpath, parent, merge = True) for fpath in pathlist]
    for item in filelist:
        item.encoded_path = xutils.encode_uri_component(item.path)
        item.icon = "fa-file-o"

        if item.type == "dir":
            item.icon = "fa-folder orange"
        elif item.ext in xconfig.FS_VIDEO_EXT_LIST:
            item.icon = "fa-file-video-o"
        elif item.ext in xconfig.FS_CODE_EXT_LIST:
            item.icon = "fa-file-code-o"
        elif item.ext in xconfig.FS_AUDIO_EXT_LIST:
            item.icon = "fa-file-audio-o"
        elif item.ext in xconfig.FS_ZIP_EXT_LIST:
            item.icon = "fa-file-zip-o"
        elif xutils.is_text_file(item.path):
            item.icon = "fa-file-text-o"
        elif xutils.is_img_file(item.path):
            item.icon = "fa-file-image-o"

    filelist.sort()
    return filelist

class FileSystemHandler:

    mime_types = xconfig.MIME_TYPES

    encodings = {
        # 二进制传输的编码格式
    }

    def handle_content_type(self, path):
        """Content-Type设置, 优先级从高到低依次是：参数配置、系统配置、默认配置"""
        type = xutils.get_argument("type")
        if type == "text":
            web.header("Content-Type", 'text/plain; charset=utf-8')
            return
        if type == "blob":
            web.header("Content-Type", self.mime_types[""])
            return
        
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
                filelist = list_win_drives()
            else:
                filelist = list_abs_dir(path)
        except OSError:
            return xtemplate.render("fs/fs.html", 
                show_aside = False,
                path = path,
                filelist = [],
                error = "No permission to list directory")

        # filelist中路径均不带/
        # 排序：文件夹优先，按字母顺序排列
        # filelist.sort(key=lambda a: a.lower())
        # filelist.sort(key=lambda a: not os.path.isdir(os.path.join(path,a)))
        filelist = process_file_list(filelist)

        # SAE上遇到中文出错
        # Fix bad filenames，修改不生效
        # filelist = list(map(lambda x: xutils.decode_bytes(x.encode("utf-8", errors='surrogateescape')), filelist))
        # Fix, some `file` in *nix is not file either directory. os.stat方法报错
        path = path.replace("\\", "/")
        kw   = get_filesystem_kw()
        kw["filelist"]     = filelist
        kw["path"]         = path
        kw["token"]        = xauth.get_current_user().token
        kw["parent_path"]  = get_parent_path(path)
        kw["search_action"] = "/fs_find"
        kw["show_aside"]   = False

        mode = xutils.get_argument("mode", xconfig.FS_VIEW_MODE)
        kw["fs_mode"] = mode
        if mode == "grid":
            return xtemplate.render("fs/fs_grid.html", **kw)
        elif mode == "shell":
            return xtemplate.render("fs/fs_shell.html", **kw)
        elif mode == "sidebar":
            kw["show_aside"] = False
            return xtemplate.render("fs/fs_sidebar.html", **kw)
        else:
            return xtemplate.render("fs/fs.html", **kw)

    def list_root(self):
        raise web.seeother("/fs//")

    def read_range(self, path, http_range, blocksize):
        xutils.trace("Download", "==> HTTP_RANGE %s" % http_range)
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

                xutils.trace("Download", "<== Content-Range:%s" % content_range)
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
                    xutils.trace("Download", "close %s" % path)
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

    def read_thumbnail(self, path, blocksize):
        dirname = os.path.dirname(path)
        fname   = os.path.basename(path)
        thumbnail_path = os.path.join(dirname, ".thumbnail", fname)
        if os.path.exists(thumbnail_path):
            return self.read_all(thumbnail_path, blocksize)
        else:
            return self.read_all(path, blocksize)

    def read_file(self, path):
        # 强制缓存
        if not xconfig.DEBUG:
            web.header("Cache-Control", "max-age=3600")

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

            if http_range is not None:
                return self.read_range(path, http_range, blocksize)
            else:
                mode = xutils.get_argument("mode", "")
                if mode == "thumbnail":
                    return self.read_thumbnail(path, blocksize)
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
        # 文件路径默认都进行urlencode
        # 如果存储结构不采用urlencode，那么这里也必须unquote回去
        if not xconfig.USE_URLENCODE:
            path = xutils.unquote(path)

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
        path = xutils.unquote(path)
        path = xutils.get_real_path(path)
        path = u(path)
        if not self.is_path_allowed(path):
            xauth.check_login("admin")
        data_prefix = u(xconfig.DATA_DIR)
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

class BaseAddFileHandler:

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument("path", "")
        filename = xutils.get_argument("filename", "")
        if path == "":
            return dict(code="fail", message="path is empty")
        if xconfig.USE_URLENCODE:
            filename = xutils.quote_unicode(filename)
        newpath = os.path.join(path, filename)
        try:
            self.create_file(newpath)
            return dict(code="success")
        except Exception as e:
            xutils.print_exc()
            return dict(code="fail", message=str(e))

    def create_file(self, path):
        raise NotImplementedError()

class AddDirHandler(BaseAddFileHandler):

    def create_file(self, path):
        os.makedirs(path)

class AddFileHandler(BaseAddFileHandler):

    def create_file(self, path):
        if os.path.exists(path):
            name = os.path.basename(path)
            raise Exception("file [%s] exists" % name)
        xutils.touch(path)

class RemoveHandler:

    @xauth.login_required()
    def POST(self):
        path = xutils.get_argument("path")
        user_name = xauth.current_name()
        if not xauth.is_admin() and not check_file_auth(path, user_name):
            return dict(code="fail", message="unauthorized")
        try:
            if not os.path.exists(path):
                basename = os.path.basename(path)
                return dict(code="fail", message="源文件`%s`不存在" % basename)
            xutils.remove(path)
            xmanager.fire("fs.remove", Storage(user = user_name, path = path))
            return dict(code="success")
        except Exception as e:
            xutils.print_exc()
            return dict(code="fail", message=str(e))
    
    def GET(self):
        return self.POST()

class RenameHandler:

    @xauth.login_required("admin")
    def POST(self):
        dirname  = xutils.get_argument("dirname")
        old_name = xutils.get_argument("old_name", "")
        new_name = xutils.get_argument("new_name", "")
        user_name = xauth.current_name()
        if old_name == "":
            return dict(code="fail", message="old_name is blank")
        if ".." in new_name:
            return dict(code="fail", message="invalid new name")
        if new_name == "":
            new_name = os.path.basename(old_name)
        if xconfig.USE_URLENCODE:
            old_name = xutils.quote_unicode(old_name)
            new_name = xutils.quote_unicode(new_name)
        old_path = os.path.join(dirname, old_name)
        new_path = os.path.join(dirname, new_name)
        if not xauth.is_admin() and not check_file_auth(old_path, user_name):
            return dict(code="fail", message="unauthorized")
        if not os.path.exists(old_path):
            return dict(code="fail", message="源文件 `%s` 不存在" % old_name)
        if os.path.exists(new_path):
            return dict(code="fail", message="目标文件 `%s` 已存在" % new_name)
        os.rename(old_path, new_path)
        xmanager.fire("fs.rename", Storage(user = user_name, path = new_path, new_path = new_path, old_path = old_path))
        return dict(code="success")

class CutHandler:

    @xauth.login_required("admin")
    def POST(self):
        files = xutils.get_argument("files[]", list())
        for i, fpath in enumerate(files):
            files[i] = os.path.abspath(fpath)
        xconfig.FS_CLIP = files
        return dict(code="success")

    def GET(self):
        return self.POST()


class PasteHandler:

    @xauth.login_required("admin")
    def POST(self):
        dirname = xutils.get_argument("dirname", "")
        old_path = xutils.get_argument("old_path", "")
        old_path = xutils.get_real_path(old_path).rstrip("/")
        old_path = os.path.abspath(old_path)
        dirname  = xutils.get_real_path(dirname)
        basename = os.path.basename(old_path)
        print(old_path, dirname, basename)
        new_path = os.path.join(dirname, basename)
        if os.path.exists(new_path):
            return dict(code="fail", message="%s 已存在" % new_path)
        os.rename(old_path, new_path)
        if xconfig.FS_CLIP != None:
            xutils.listremove(xconfig.FS_CLIP, old_path)
        return dict(code="success")

class ClearClipHandler:

    @xauth.login_required("admin")
    def POST(self):
        xconfig.FS_CLIP = None
        return dict(code="success")

    def GET(self):
        return self.POST()

class ListDirHandler:

    @xauth.login_required("admin")
    def GET(self):
        datapath = u(os.path.abspath(xconfig.DATA_DIR))
        raise web.seeother("/fs/%s" % datapath)

class LinkHandler:

    @xauth.login_required("admin")
    def GET(self, name):
        if name == "home":
            link_path = "./"
            if xutils.is_mac():
                link_path = os.environ['HOME']
            if xutils.is_windows():
                link_path = os.path.join(os.environ['HOMEDRIVE'], os.environ['HOMEPATH'])
        else:
            link_path = os.path.join(xconfig.DATA_DIR, name)
        
        link_path = os.path.abspath(link_path)
        raise web.seeother("/fs/%s" % link_path)

class RecentHandler:

    @xauth.login_required("admin")
    def GET(self):
        datapath, webpath = xutils.get_upload_file_path(xauth.current_name(), "")
        raise web.seeother("/fs/%s" % datapath)

class ViewHandler:

    @xauth.login_required("admin")
    def GET(self):
        fpath = xutils.get_argument("path")
        basename, ext = os.path.splitext(fpath)
        encoded_fpath = xutils.encode_uri_component(fpath)

        if ext == ".txt":
            raise web.found("/fs_text?path=%s" % encoded_fpath)

        if ext in (".html", ".htm"):
            raise web.found("/fs/%s" % encoded_fpath)

        if ext in (".md", ".csv"):
            raise web.found("/code/preview?path=%s" % encoded_fpath)

        if ext == ".db":
            raise web.found("/tools/sql?path=%s" % encoded_fpath)

        if xutils.is_text_file(fpath):
            raise web.found("/code/edit?path=%s" % encoded_fpath)

        raise web.found("/fs/%s" % encoded_fpath)


class EditHandler:

    @xauth.login_required("admin")
    def GET(self):
        fpath = xutils.get_argument("path")
        basename, ext = os.path.splitext(fpath)
        encoded_fpath = xutils.encode_uri_component(fpath)

        if xutils.is_text_file(fpath):
            raise web.found("/code/edit?path=%s" % encoded_fpath)

        raise web.found("/fs_hex?path=%s" % encoded_fpath)

class TextHandler:

    @xauth.login_required("admin")
    def GET(self):
        return xtemplate.render("fs/template/txtreader.html")

xutils.register_func("fs.process_file_list", process_file_list)

xurls = (
    r"/fs_list/?", ListDirHandler,
    r"/fs_edit",   EditHandler,
    r"/fs_view",   ViewHandler,
    r"/fs_text",   TextHandler,
    r"/fs_api/add_dir", AddDirHandler,
    r"/fs_api/add_file", AddFileHandler,
    r"/fs_api/remove", RemoveHandler,
    r"/fs_api/rename", RenameHandler,
    r"/fs_api/cut", CutHandler,
    r"/fs_api/paste", PasteHandler,
    r"/fs_api/clear_clip", ClearClipHandler,
    r"/fs_link/(.*)", LinkHandler,
    r"/fs_recent", RecentHandler,
    r"/fs/(.*)", FileSystemHandler,
    r"/(static/.*)", StaticFileHandler,
    r"/data/(.*)", StaticFileHandler,
    r"/(app/.*)", StaticFileHandler,
    r"/(tmp/.*)", StaticFileHandler,
)


