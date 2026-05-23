# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# @modified 2022/04/10 18:33:45

"""xnote文件服务，主要功能:
1. 静态文件服务器，生产模式使用强制缓存，开发模式使用协商缓存
2. 文件浏览器
3. 文件下载，支持断点续传
4. 文件上传

PS. 类似的功能可以参考 webdav
"""
import os
import sys
import time
import datetime

import mimetypes
import web
from xnote_handlers.config import LinkConfig
import xutils
import logging
import zipfile

from io import BufferedReader
from typing import List, Optional
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.core import xnote_event

from xutils import FileItem, u, Storage, fsutil
from xutils import dbutil
from xutils import webutil
from xutils import XnoteException
from xutils import ziputil
from xutils import textutil

from .fs_mode import get_fs_page_by_mode
from .fs_helper import sort_files_by_size, is_hidden_file
from . import fs_image
from . import fs_helper
from . import fs_checker
from .fs_dao import FileInfoDao

from xnote.plugin import ActionBar

# 配置文件
# 强制使用Range请求的文件大小阈值（超过此大小的文件首次请求时只返回部分内容）
FORCE_RANGE_THRESHOLD = 10 * 1024 * 1024   # 10MB
# 强制Range请求时返回的初始数据大小（必须足够大以包含moov盒子）
# 4K视频moov盒子可能很大（包含大量样本表），建议设置3MB以上
FORCE_RANGE_DATA_SIZE = 4 * 1024 * 1024  # 4MB

READ_BUF_SIZE = 64 * 1024 # 64K

def is_stared(path):
    return xconfig.has_config("STARED_DIRS", path)

def get_file_size(filepath):
    return fsutil.get_file_size(filepath, format=True)

def get_filesystem_kw():
    """return filesystem utils"""
    kw = Storage()
    kw["os"]            = os
    kw["search_type"]   = "fs"
    kw["get_file_size"] = get_file_size
    kw["html_title"]    = "文件"
    kw._show_footer = False
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

def get_user_home_path(user_name):
    datapath = u(os.path.abspath(xconfig.DATA_DIR))
    return os.path.join(datapath, "files", user_name) 

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

def list_file_objects(fpath: str):
    if xutils.is_windows() and fpath == "/":
        filenames = list_win_drives()
    else:
        filenames = list_abs_dir(fpath)
    return process_file_list(filenames)

def check_file_auth(path, user_name):
    user_dir = os.path.join(xconfig.UPLOAD_DIR, user_name)
    path = os.path.abspath(path)
    return path.startswith(user_dir)

def process_file_list(pathlist: List[str], parent:Optional[str] = None):
    filelist = [FileItem(fpath, parent, merge = False) for fpath in pathlist]
    filelist.sort()

    def filter_func(item: FileItem):
        if is_hidden_file(item):
            return False
        fs_helper.handle_file_item(item)
        return True

    filelist = list(filter(filter_func, filelist))

    user_id = xauth.current_user_id()
    fs_order = xauth.get_user_config(user_id, "fs_order")
    if fs_order == "size":
        sort_files_by_size(filelist)
    return filelist

class FileSystemHandler:

    mime_types = xconfig.MIME_TYPES

    encodings = {
        # 二进制传输的编码格式
    }

    def handle_content_type(self, path: str, content_type = None):
        """Content-Type设置, 优先级从高到低依次是：参数配置、系统配置、默认配置"""
        if content_type != None:
            web.header("Content-Type", content_type)
            return
            
        type = xutils.get_argument_str("type")
        path = xutils.decode_name(path)

        if type == "text":
            web.header("Content-Type", 'text/plain; charset=utf-8')
            return
        
        if type == "blob":
            web.header("Content-Type", self.mime_types[""])
            fname = os.path.basename(path)
            fname = xutils.quote_unicode(fname)
            web.header("Content-Disposition", "attachment; filename=\"%s\"" % fname)
            return
        
        name, ext = os.path.splitext(path)
        mime_type = self.mime_types.get(ext.lower())
        if mime_type is None:
            mime_type, mime_encoding = mimetypes.guess_type(path)
        if mime_type is None:
            mime_type = self.mime_types['']

        web.header("Content-Type", mime_type)

    def handle_content_encoding(self, ext):
        """Content-Encoding设置，这里应该是二进制编码格式"""
        if ext in self.encodings:
            web.header("Content-Encoding", self.encodings[ext])

    def list_directory(self, path: str):
        try:
            filelist = list_file_objects(path)
            parent_file = fs_helper.get_parent_file_object(path, "[上级目录]")
            if not fsutil.is_same_file(parent_file.path, path):
                filelist.insert(0, parent_file)
        except OSError:
            return xtemplate.render("fs/page/fs.html", 
                show_aside = False,
                path = path,
                filelist = [],
                error = "No permission to list directory")
            
        return self.render_file_list(path, filelist)

    def render_file_list(self, path: str, filelist: List[FileItem], fs_path_list = []):
        # filelist中路径均不带/
        # 排序：文件夹优先，按字母顺序排列
        # filelist.sort(key=lambda a: a.lower())
        # filelist.sort(key=lambda a: not os.path.isdir(os.path.join(path,a)))

        # SAE上遇到中文出错
        # Fix bad filenames，修改不生效
        # filelist = list(map(lambda x: xutils.decode_bytes(x.encode("utf-8", errors='surrogateescape')), filelist))
        # Fix, some `file` in *nix is not file either directory. os.stat方法报错
        path           = path.replace("\\", "/")
        kw             = get_filesystem_kw()
        kw.filelist    = filelist
        kw.path        = path
        kw.quoted_path = xutils.quote(path)
        kw.fs_path_list = fs_path_list
        kw.fs_upload_action = "fs_upload_to_dir"
        user_info = xauth.current_user()
        assert isinstance(user_info, Storage)

        kw["token"]         = user_info.token
        kw["parent_path"]   = get_parent_path(path)
        kw["search_action"] = "/fs_find"
        kw["show_aside"]    = False

        mode = xutils.get_argument_str("mode", xconfig.FS_VIEW_MODE)
        kw["fs_mode"] = mode
        return get_fs_page_by_mode(mode, kw)

    def list_root(self):
        raise web.seeother("/fs/~/")

    def read_range(self, path:str, http_range:str, blocksize:int):
        logging.debug("read_range HTTP_RANGE %s", http_range)
        range_list = http_range.split("bytes=")
        if len(range_list) == 2:
            # 包含完整的范围
            range_list = range_list[1]
            try:
                range_start, range_end = range_list.split('-')
                range_start = int(range_start)
                total_size = os.stat(path).st_size
                if range_end != "":
                    # 浏览器指定了结束位置
                    range_end = min(int(range_end), total_size - 1, range_start + FORCE_RANGE_DATA_SIZE - 1)
                else:
                    # 浏览器未指定结束位置，只返回一个数据块（1MB）
                    # 避免一次性传输过多数据，让浏览器继续发送Range请求
                    range_end = min(range_start + FORCE_RANGE_DATA_SIZE - 1, total_size - 1)
                content_length = range_end - range_start + 1
                web.header("Content-Length", content_length)
                content_range = "bytes %s-%s/%s" % (range_start, range_end, total_size)
                # 设置HTTP响应状态
                web.ctx.status = "206 Partial Content"
                # 发送HTTP首部
                web.header("Accept-Ranges", "bytes")
                web.header("Content-Range", content_range)
                logging.debug("resp Content-Range:%s", content_range)
                
                # 发送数据
                logging.debug("open file %s, range: %s-%s", path, range_start, range_end)
                with open(path, "rb") as fp:
                    fp.seek(range_start)
                    yield from self._read_block(fp, content_length)
                    logging.debug("file %s sent %s bytes\n", path, fsutil.format_size(content_length))
            except ValueError as e:
                # Range 解析错误（如非数字），返回 416 Range Not Satisfiable
                logging.warning("Range parse error: %s, range: %s", e, http_range)
                web.ctx.status = "416 Range Not Satisfiable"
                web.header("Content-Range", "bytes */%s" % os.stat(path).st_size)
                yield b""
            except Exception as e:
                # 其他未知异常，返回 500
                logging.error("Range request error: %s", e)
                xutils.print_stacktrace()
                web.ctx.status = "500 Internal Server Error"
                yield b""
        else:
            # 处理不了Range格式，返回所有的数据（200 OK）
            yield self.read_all(path, blocksize)

    def read_all(self, path: str, blocksize: int):
        total_size = os.stat(path).st_size
        web.header("Content-Length", total_size)
        logging.debug("read_all Content-Length %s", total_size)
        with open(path, "rb") as fp:
            block = fp.read(blocksize)
            while block:
                # print("%s Read %s K" % (time.ctime(), blocksize))
                yield block
                block = fp.read(blocksize)

    def read_range_initial(self, path: str, total_size: int):
        # 大文件首次请求时，返回初始数据并使用206状态码
        # 这样浏览器会继续使用Range请求分段加载，避免一次性传输大文件
        initial_size = min(FORCE_RANGE_DATA_SIZE, total_size)
        range_end = initial_size - 1

        content_range = "bytes %s-%s/%s" % (0, range_end, total_size)
        web.ctx.status = "206 Partial Content"
        web.header("Content-Length", initial_size)
        web.header("Content-Range", content_range)
        # 告诉浏览器支持断点续传（Range请求）
        web.header("Accept-Ranges", "bytes")
        
        logging.debug("read_range_initial: %s, range: %s", path, content_range)

        with open(path, "rb") as fp:
            yield from self._read_block(fp, initial_size)
            logging.debug("file %s sent %s bytes\n", path, fsutil.format_size(initial_size))
            
    def _read_block(self, fp: BufferedReader, read_size:int):
        rest = read_size
        while rest > 0:
            min_buf_size = min(rest, READ_BUF_SIZE)
            buf = fp.read(min_buf_size)
            rest -= len(buf)
            logging.debug("read buf %s, rest %s", len(buf), rest)
            if not buf:
                break
            yield buf
        logging.debug("_read_block end")

    def read_thumbnail(self, path, blocksize: int, version="v1"):
        # TODO 限制进程数量
        # 在SAE环境中，pillow处理图片后无法释放内存，改成用子进程处理
        data = fs_image.create_thumbnail_data(path, version)
        if data != None:
            yield data
        else:
            yield from self.read_all(path, blocksize)
    
    def set_cache_control(self, mtime, etag, expire_days=30):
        # 如果Edge浏览器没有按照cache-control的建议执行，将浏览器设置重置
        # 需要注意的是，服务器端在生成状态码为 304 的响应的时候，必须同时生成
        # 以下会存在于对应的 200 响应中的首部：
        # Cache-Control、Content-Location、Date、ETag、Expires 和 Vary。
        # HTTP/1.0的缓存header是Expires
        # HTTP/1.1的缓存首部是Cache-Control
        expire_seconds = expire_days * 3600 * 24
        expire_time = datetime.datetime.utcnow() + datetime.timedelta(days=expire_days)
        # 强制开启缓存
        web.header("Cache-Control", f"public, max-age={expire_seconds}")

        # DEBUG模式会刷新ts
        # 在发布缓存副本之前，强制要求缓存把请求提交给原始服务器进行验证 (协商缓存验证)。
        # web.header("Cache-Control", "no-cache")
        
        modified = time.gmtime(mtime)
        web.header("Last-Modified", time.strftime("%a, %d %b %Y %H:%M:%S GMT", modified))
        web.header("Expires", expire_time.strftime("%a, %d %b %Y %H:%M:%S GMT"))
        web.header("Etag", etag)
        web.header("Content-Location", web.ctx.fullpath)
        web.header("Vary", "Accept-Encoding") # 请求编码变化时缓存失效
        # web.header("Vary", "User-Agent") # User-Agent变化时缓存失效

    def read_file(self, path, content_type=None):
        environ = web.ctx.environ
        mtime = os.path.getmtime(path)
        etag = '"%s"' % mtime
        client_etag = environ.get('HTTP_IF_NONE_MATCH')

        if etag == client_etag:
            web.ctx.status = "304 Not Modified"
            return b'' # 其实webpy已经通过yield空bytes来避免None

        self.handle_content_type(path, content_type)

        http_range = environ.get("HTTP_RANGE")
        blocksize = 64 * 1024 # 64K

        if http_range is not None:
            return self.read_range(path, http_range, blocksize)
        else:
            mode = xutils.get_argument("mode", "")
            if mode == "thumbnail":
                return self.read_thumbnail(path, blocksize)
            if mode == "thumbnail_v2":
                # 等比例缩放
                return self.read_thumbnail(path, blocksize, version="v2")
            # 对于大文件，首次请求返回部分内容（206），让浏览器使用Range请求分段加载
            # 如果moov盒子不完整，浏览器会发送新的Range请求继续获取
            total_size = os.stat(path).st_size
            if total_size > FORCE_RANGE_THRESHOLD:
                return self.read_range_initial(path, total_size)
            
            self.set_cache_control(mtime, etag)
            return self.read_all(path, blocksize)            

    def handle_get(self, path: str, content_type=None):
        if path == "":
            return self.list_root()
        if os.path.isdir(path):
            return self.list_directory(path)
        elif os.path.isfile(path):
            return self.read_file(path, content_type=content_type)
        else:
            # return "Not Readable %s" % path
            extra = "class = FileSystemHandler"
            return self.render_not_readable(path, extra=extra)

    def render_not_readable(self, path: str, extra = ""):
        web.ctx.status = "404 Not Found"
        return xtemplate.render("fs/page/fs_not_readable.html", path = path, extra = extra)

    def resolve_fpath(self, path: str):
        # fpath参数使用b64编码
        fpath = xutils.get_argument_str("fpath")
        if fpath != "":
            return xutils.decode_base64(fpath)

        if not xconfig.USE_URLENCODE:
            path = xutils.unquote(path)

        if not os.path.exists(path):
            # /fs/ 文件名来源是文件系统提供的，尝试unquote不会出现问题
            path = xutils.unquote(path)

        return path

    @xauth.login_required("admin")
    def GET(self, path = ""):
        # 文件路径默认都进行urlencode
        # 如果存储结构不采用urlencode，那么这里也必须unquote回去
        path = self.resolve_fpath(path)
        return self.handle_get(path)
            

class DocFileHandler:

    fs_handler = FileSystemHandler()

    def GET(self):
        fpath = xutils.get_argument("fpath", "")
        assert isinstance(fpath, str)
        if fpath == "":
            raise web.notfound()
        if ".." in fpath:
            raise web.badrequest()
        fpath = os.path.join("./docs", fpath)
        return self.fs_handler.handle_get(fpath)


def check_token_or_admin():
    token = xutils.get_argument_str("token")
    if token != "":
        from xnote_handlers.system.system_sync.dao import SystemSyncTokenDao
        token_info = SystemSyncTokenDao.get_by_token(token)
        if token_info is None or token_info.is_expired():
            raise web.Forbidden(message="invalid token")
        # token is ok
    else:
        xauth.check_login("admin")
        

class StaticFileHandler(FileSystemHandler):
    allowed_prefix = ["static", "img", "app", "files", "tmp", "scripts"]

    def is_path_allowed(self, path):
        if ".." in path:
            return False
        for prefix in self.allowed_prefix:
            if path.startswith(prefix):
                return True
        return False

    """外置数据的静态文件支持"""
    def GET(self, path = ""):
        origin_path = path
        path = xutils.unquote(path)
        if not self.is_path_allowed(path):
            check_token_or_admin()

        data_prefix = u(xconfig.DATA_DIR)
        if not path.startswith("static"):
            newpath = os.path.join(data_prefix, path)
        else:
            # /static/xxx 文件
            newpath = xconfig.resolve_config_path(path)
            # 兼容static目录数据
            if not os.path.exists(newpath):
                static_prefix_len = len("static/")
                newpath = os.path.join(data_prefix, path[static_prefix_len:])

        path = xutils.get_real_path(newpath)
        if not os.path.isfile(path):
            # 静态文件不允许访问文件夹
            web.ctx.status = "404 Not Found"
            return f"Invalid File Path: {origin_path}"
        return self.handle_get(path)


class DownloadHandler(FileSystemHandler):

    def GET(self, path = ""):
        check_token_or_admin()
        path = self.resolve_fpath(path)
        return self.handle_get(path)

class GetFileHandler(DownloadHandler):
    pass

class RemoveAjaxHandler:

    @xauth.login_required()
    def POST(self):
        path = xutils.get_argument_str("path")
        assert isinstance(path, str)
        user_name = xauth.current_name_str()
        user_id = xauth.current_user_id()

        if not xauth.is_admin() and not check_file_auth(path, user_name):
            return webutil.FailedResult(code="fail", message="unauthorized")
        try:
            if not os.path.exists(path):
                FileInfoDao.delete_by_fpath(path)
                basename = os.path.basename(path)
                return webutil.FailedResult(code="fail", message="源文件`%s`不存在" % basename)
            xutils.remove(path)

            event = xnote_event.FileDeleteEvent()
            event.fpath = path
            event.user_name = user_name
            event.user_id = user_id
            event.fire()

            return webutil.SuccessResult()
        except Exception as e:
            xutils.print_exc()
            return webutil.FailedResult(code="fail", message=str(e))
    
    def GET(self):
        return self.POST()

class RenameAjaxHandler:

    def POST(self):
        try:
            return self.do_post()
        except XnoteException as e:
            return webutil.FailedResult(code=e.code, message=e.message)

    @xauth.login_required("admin")
    def do_post(self):
        dirname  = xutils.get_argument_str("dirname")
        old_name = xutils.get_argument_str("old_name", "")
        new_name = xutils.get_argument_str("new_name", "")
        user_info = xauth.current_user()
        assert user_info != None

        user_name = user_info.name

        if dirname is None or dirname == "":
            return webutil.FailedResult(code="fail", message="dirname is blank")
        
        if old_name is None or old_name == "":
            return webutil.FailedResult(code="fail", message="old_name is blank")

        fs_checker.check_file_name(new_name)
        
        logging.info("encode_name=%s, new_name=%s", xconfig.USE_URLENCODE, new_name)

        if xconfig.USE_URLENCODE:
            new_name = fsutil.get_safe_file_name(new_name)

        old_path = os.path.join(dirname, old_name)
        new_path = os.path.join(dirname, new_name)

        # 获取真实的路径
        old_path = xutils.get_real_path(old_path)

        if not xauth.is_admin() and not check_file_auth(old_path, user_name):
            return webutil.FailedResult(code="fail", message="unauthorized")
        if not os.path.exists(old_path):
            return webutil.FailedResult(code="fail", message="源文件 `%s` 不存在" % old_name)
        if os.path.exists(new_path):
            return webutil.FailedResult(code="fail", message="目标文件 `%s` 已存在" % new_name)
        os.rename(old_path, new_path)

        event = xnote_event.FileRenameEvent()
        event.fpath = new_path
        event.old_fpath = old_path
        event.user_name = user_name
        event.user_id = user_info.id
        event.fire()

        return webutil.SuccessResult()

class CutAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        files = xutils.get_argument("files[]", list())
        assert isinstance(files, list)
        for i, fpath in enumerate(files):
            files[i] = os.path.abspath(fpath)
        xconfig.FS_CLIP = files
        return webutil.SuccessResult()

    def GET(self):
        return self.POST()


class PasteAjaxHandler:

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

class ClearClipAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        xconfig.FS_CLIP = None
        return dict(code="success")

    def GET(self):
        return self.POST()

class ListAjaxHandler:

    @xauth.login_required("admin")
    def GET(self):
        fpath = xutils.get_argument_str("fpath")
        show_parent = xutils.get_argument_str("show_parent")

        if fpath == "" or fpath == None:
            return webutil.FailedResult(code = "400", message = u"fpath参数为空")

        if not os.path.exists(fpath):
            return webutil.FailedResult(code = "404", message = u"文件不存在")

        files = list_file_objects(fpath)
        if show_parent == "true":
            files.insert(0, fs_helper.get_parent_file_object(fpath, "[上级目录]"))

        result = webutil.SuccessResult(files)
        result.fpath = fpath
        return result

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
        raise web.seeother("/fs/~%s" % link_path)

class Bookmark:

    def __init__(self, user_name):
        self.user_name = user_name
        bookmark = dbutil.get("fs_bookmark:%s" % user_name)
        if bookmark is None:
            bookmark = []
        assert isinstance(bookmark, list)
        self.bookmark = bookmark

        for i, value in enumerate(bookmark):
            bookmark[i] = fsutil.normalize_path(value)

    def append(self, path):
        if path not in self.bookmark:
            self.bookmark.append(path)

    def remove(self, path):
        if path in self.bookmark:
            self.bookmark.remove(path)

    def get(self):
        self.bookmark = list(filter(lambda x:x!=None and os.path.exists(x), self.bookmark))
        return self.bookmark

    def save(self):
        print("save: ", self.bookmark)
        dbutil.put("fs_bookmark:%s" % self.user_name, self.bookmark)


class BookmarkHandler:
    @xauth.admin_required()
    def GET(self):
        user_name = xauth.current_name_str()

        xmanager.add_visit_log(user_name, "/fs_bookmark")

        kw = Storage()
        bookmark = Bookmark(user_name)

        filelist = []
        filelist.append(FileItem("/", name = "操作系统根目录"))
        os_user_home_path = os.path.expanduser("~")
        filelist.append(FileItem(os_user_home_path, name = "操作系统用户目录"))
        filelist.append(FileItem(xconfig.DATA_DIR, name = "Xnote数据目录"))
        
        for fpath in bookmark.get():
            item = FileItem(fpath)
            item.is_user_defined = True
            filelist.append(item)
        
        for item in filelist:
            fs_helper.handle_file_item(item)

        kw.show_path = False
        kw.show_fake_path = True
        kw.fake_path_url = "/fs_bookmark"
        kw.fake_path_name = "文件收藏夹"
        kw.filelist = filelist
        kw.fs_toolbar = self.get_fs_toolbar()
        kw.parent_link = LinkConfig.app_index
        
        return xtemplate.render("fs/page/fs_bookmark.html", **kw)
    
    def get_fs_toolbar(self):
        fs_toolbar = ActionBar("card btn-line-height")
        fs_toolbar.add_span("工具: ", css_class="card-title-span")
        fs_toolbar.add_nbsp()
        fs_toolbar.add_link(text="侧边栏视图", href=fs_helper.get_fs_url(xconfig.DATA_DIR) + "?mode=sidebar")
        fs_toolbar.add_item_sep()
        fs_toolbar.add_link(text="上传文件", href="/fs_upload/manage")
        fs_toolbar.add_item_sep()
        fs_toolbar.add_link(text="更多工具", href="/plugin_list?category=dir&show_back=true")
        return fs_toolbar

class UserHomeHandler(BookmarkHandler):
    pass

class BookmarkAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        user_name = xauth.current_name()
        path = xutils.get_argument("path")
        action = xutils.get_argument("action")
        bookmark = Bookmark(user_name)

        if action == "remove":
            bookmark.remove(path)
        else:
            bookmark.append(path)
        
        bookmark.save()
        return dict(code = "success")

class ToolListHandler:

    @xauth.login_required("admin")
    def GET(self):
        raise web.found("/plugin_list?category=dir&show_back=true")


    
dbutil.register_table("fs_bookmark", "文件收藏夹")
xutils.register_func("fs.process_file_list", process_file_list)

xurls = (
    r"/fs_link/(.*)", LinkHandler,
    r"/fs_tools",  ToolListHandler,

    # Ajax服务
    r"/fs_api/remove", RemoveAjaxHandler,
    r"/fs_api/rename", RenameAjaxHandler,
    r"/fs_api/cut",   CutAjaxHandler,
    r"/fs_api/paste", PasteAjaxHandler,
    r"/fs_api/clear_clip", ClearClipAjaxHandler,
    r"/fs_api/bookmark", BookmarkAjaxHandler,
    r"/fs_api/list", ListAjaxHandler,

    r"/fs_list/?",   UserHomeHandler,
    r"/fs_bookmark", BookmarkHandler,

    r"/fs/~(.*)", FileSystemHandler,
    r"/fs_download", DownloadHandler,
    r"/fs_get"     , GetFileHandler,
    r"/(static/.*)", StaticFileHandler,
    # `/static/.*` 路径是`web.py`自带的中间件处理的，优先级更高，所以这里加了一个前缀用以区分
    r"/_(static/.*)", StaticFileHandler,
    r"/data/(.*)", StaticFileHandler,
    r"/(app/.*)", StaticFileHandler,
    r"/(tmp/.*)", StaticFileHandler,
    r"/fs_doc", DocFileHandler,
)


