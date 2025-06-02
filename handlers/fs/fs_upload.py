# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2017
# @modified 2021/07/31 14:27:13
import os
import web
import logging
import time
import math
import xutils

from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xtemplate
from xnote.core import xmanager
from xutils import fsutil, Storage, dateutil
from xutils import webutil
from xutils.base import XnoteException
from xnote.core.xtemplate import T
from xnote.core.xnote_event import FileUploadEvent
from .fs_helper import FileInfoDao
from handlers.fs import fs_checker
from xutils.fsutil import get_safe_file_name
from handlers.note.models import NoteTypeInfo

try:
    from PIL import Image
except ImportError:
    Image = None

# 完整的元信息参考文档 https://zhuanlan.zhihu.com/p/366726838
TAG_ORIENTATION = 0x112


def get_link(filename, webpath):
    """返回Markdown的链接"""
    if xutils.is_img_file(filename):
        return "![%s](%s)" % (filename, webpath)
    return "[%s](%s)" % (filename, webpath)


def generate_filename(filename, prefix="", ext=None):
    if prefix:
        prefix = prefix + '_'
    else:
        prefix = ""

    if filename is None:
        filename = time.strftime("%Y%m%d")
        filename += "_" + xutils.create_uuid()
    filename = get_safe_file_name(filename)
    if ext:
        filename += ext
    return prefix + filename

def get_auto_filename(ext=""):
    return xutils.create_uuid() + ext

def get_display_name(fpath, parent):
    path = xutils.get_relative_path(fpath, parent)
    return xutils.unquote(path)

def get_webpath(fpath):
    rpath = xutils.get_relative_path(fpath, xconfig.DATA_DIR)
    return "/data/" + rpath


def upload_link_by_month(year, month, delta=0):
    t_mon = (month - 1 + delta) % 12 + 1
    t_year = year + math.floor((month-1+delta)/12)
    return "/fs_upload?year=%d&month=%02d" % (t_year, t_mon)


def try_touch_note(note_id):
    if note_id != None and note_id != "":
        xutils.call("note.touch", note_id)

def try_fix_orientation(fpath):
    fix_orientation = xutils.get_argument_bool("fix_orientation", False)
    # print("fix_orientation", fix_orientation)
    if not fix_orientation:
        return

    if Image == None:
        # 没有安装PIL
        return

    name, ext = os.path.splitext(fpath)
    if ext.lower() not in (".jpg", ".jpeg"):
        return

    tmp_path = fsutil.tmp_path(xutils.create_uuid())
    os.rename(fpath, tmp_path)
    rename_back = False

    with Image.open(tmp_path) as img:
        exif = img.getexif()
        # print("exif", exif)
        orientation = exif.get(TAG_ORIENTATION)

        if orientation in (3, 6):
            logging.info("fix orientation, fpath=%s", fpath)
            img_new = img.copy()
            exif_new = img_new.getexif()
            exif_new[TAG_ORIENTATION] = 1
            img_new.save(fpath)
            img_new.close()
            os.remove(tmp_path)
        else:
            # 重新命名回去
            # 需要先关闭文件,然后再重命名,不然可能触发文件操作冲突
            rename_back = True

    if rename_back:
        os.rename(tmp_path, fpath)

# 业务上用到的函数

def get_user_upload_dir(user):
    return os.path.join(xconfig.UPLOAD_DIR, user)

def get_auto_file_path(filename: str):
    """filename 默认是 uuid4 32位字符串
    先使用两层文件夹,如果文件夹里面最多256个文件,可以支持 `256*256*256 = 1677万` 个文件
    """
    assert len(filename) > 10
    first_dir = filename[0:2]
    second_dir = filename[2:4]
    dirname = os.path.join(xconfig.FileConfig.files_dir, first_dir, second_dir)
    fsutil.makedirs(dirname)
    fpath = os.path.join(dirname, filename)
    # 虽然概率极低，最好还是check下文件名是否重复
    if os.path.exists(fpath):
        raise Exception("文件名冲突,请重试")
    return os.path.abspath(fpath), get_webpath(fpath)


def get_upload_file_path(user, filename, upload_dir="files", rename_conflict=False):
    """生成上传文件名"""
    from xnote.core import xconfig
    if xconfig.USE_URLENCODE:
        origin_filename = filename
        filename = xutils.quote_unicode(filename)
        if origin_filename != filename:
            filename = xutils.encode_name(filename)

    basename, ext = os.path.splitext(filename)
    date = time.strftime("upload/%Y/%m")
    dirname = os.path.join(xconfig.DATA_PATH, upload_dir, user, date)
    fsutil.makedirs(dirname)

    origin_filename = os.path.join(dirname, filename)
    fileindex = 1

    newfilepath = origin_filename
    webpath = "/data/{}/{}/{}/{}".format(upload_dir, user, date, filename)
    if filename == "":
        # get upload directory
        return os.path.abspath(dirname), webpath

    while not rename_conflict and os.path.exists(newfilepath):
        name, ext = os.path.splitext(filename)
        # 使用下划线，括号会使marked.js解析图片url失败
        temp_filename = "{}_{}{}".format(name, fileindex, ext)
        newfilepath = os.path.join(dirname, temp_filename)
        webpath = "/data/{}/{}/{}/{}".format(upload_dir,
                                             user, date, temp_filename)
        fileindex += 1
    return os.path.abspath(newfilepath), webpath


class UploadHandler:

    def get_recovery_path(self, fpath=""):
        fpath = fpath.replace(xconfig.FileReplacement.data_dir, xconfig.FileConfig.data_dir)
        return fpath, fsutil.get_webpath(fpath)

    @xauth.login_required()
    def POST(self):
        try:
            return self.do_post()
        except XnoteException as e:
            return webutil.FailedResult(code=e.code, message=e.message)
        except Exception as e:
            err_stack = xutils.print_exc()
            err_msg = str(e)
            if xauth.is_admin():
                err_msg = err_stack
            return webutil.FailedResult(code="500", message=err_msg)
        
    def do_post(self):
        file = xutils.get_argument_field_storage("file")
        name = xutils.get_argument_str("name")
        note_id = xutils.get_argument_str("note_id")
        upload_type = xutils.get_argument_str("upload_type")

        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name
        user_id = user_info.user_id
        webpath = ""
        filename = ""

        if file.file is None:
            return webutil.FailedResult(code="400", message="file.file is None")
        
        if file.filename is None:
            return webutil.FailedResult(code="400", message="file.filename is None")
        
        logging.info("upload filename=%s, length=%s", file.filename, file.length)
        
        # 检查文件大小
        fs_checker.check_upload_size(file.length)
        
        # 扩展名要从原始的文件名获取
        _, ext = os.path.splitext(file.filename)

        # iOS上传文件截图文件固定是image.png
        filename = get_auto_filename(ext)

        if upload_type == "recovery":
            if not xauth.is_admin():
                return webutil.FailedResult(code="403", message="recovery mode is only allowed by admin")
            filepath, webpath = self.get_recovery_path(filename)
            dirs = os.path.dirname(filepath)
            fsutil.makedirs(dirs)
        else:
            filepath, webpath = get_auto_file_path(filename)
        
        tmp_file = os.path.join(xconfig.FileConfig.tmp_dir, filename)
        tmp_file += ".upload"

        upload_size = 0
        with open(tmp_file, "wb") as fout:
            for chunk in file.file:
                upload_size += len(chunk)
                try:
                    fs_checker.check_upload_size(upload_size)
                except Exception as e:
                    # 检查失败,删除临时文件
                    fsutil.remove_file(tmp_file)
                    raise e
                fout.write(chunk)

        sha256 = fsutil.get_sha256_sum(tmp_file)
        file_info = FileInfoDao.get_by_sha256(user_id=user_id, sha256=sha256)
        if file_info != None:
            fsutil.remove_file(tmp_file, hard=True)
            # 已经上传过,直接复用
            result = webutil.SuccessResult()
            result.webpath = fsutil.get_webpath(file_info.realpath)
            result.link = get_link(file.filename, webpath)
            return result
        
        # 上传成功后重命名
        os.rename(tmp_file, filepath)
        
        # 需要先处理旋转,不然触发upload事件可能导致文件操作冲突
        try_fix_orientation(filepath)
        try_touch_note(note_id)

        event = FileUploadEvent()
        event.fpath = filepath
        event.user_name = user_info.name
        event.user_id = user_info.id
        event.remark = file.filename
        xmanager.fire("fs.upload", event)

        result = webutil.SuccessResult()
        result.webpath = webpath
        result.link = get_link(file.filename, webpath)
        return result

    @xauth.login_required()
    def GET(self):
        return self.get_upload_page_v2()

    def get_upload_page_v2(self):
        # TODO 基于数据库数据的上传页面
        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name
        xmanager.add_visit_log(user_name, "/fs_upload")

        year = xutils.get_argument_int("year", dateutil.get_current_year())
        month = xutils.get_argument_int("month", dateutil.get_current_month())

        date_info = dateutil.DateInfo(year=year, month=month)

        user_id = user_info.id
        start_time = date_info.format_date()
        end_time = date_info.next_month().format_date()
        files = FileInfoDao.list(user_id=user_id, limit=50, start_time_inclusive=start_time, end_time_exclusive=end_time)
        pathlist = []
        for item in files:
            pathlist.append(item.realpath)
        
        kw = Storage()
        kw.html_title = T("文件")
        kw.files = files
        kw.pathlist = pathlist
        kw.year = int(year)
        kw.month = int(month)
        kw.path = ""
        kw.dirname = ""
        kw.get_webpath = get_webpath
        kw.upload_link_by_month = upload_link_by_month
        kw.get_display_name = get_display_name
        kw.type_list = NoteTypeInfo.get_type_list()
        kw.note_type = "file"

        return xtemplate.render("fs/page/fs_upload.html",**kw)
    

class RangeUploadHandler:

    def merge_files(self, dirname, filename, chunks):
        dest_path = os.path.join(dirname, filename)
        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name

        with open(dest_path, "wb") as fp:
            for chunk in range(chunks):
                filename = get_safe_file_name(filename)
                tmp_path = os.path.join(dirname, filename)
                tmp_path = "%s_%d.part" % (tmp_path, chunk)
                if not os.path.exists(tmp_path):
                    raise Exception("upload file broken")
                with open(tmp_path, "rb") as tmp_fp:
                    fp.write(tmp_fp.read())
                xutils.remove(tmp_path, True)

            event = FileUploadEvent()
            event.user_name = user_name
            event.user_id = user_info.id
            event.fpath = dest_path
            xmanager.fire("fs.upload", event)

    def is_fixed_name(self, filename):
        name, ext = os.path.splitext(filename)
        return name == "image"

    def find_available_path(self, filename):
        name, ext = os.path.splitext(filename)
        assert name == "image"
        return name + "_" + xutils.create_uuid() + ext

    def POST(self):
        try:
            return self.do_post()
        except XnoteException as e:
            return webutil.FailedResult(code=e.code, message=e.message)

    @xauth.login_required()
    def do_post(self):
        return webutil.FailedResult(code="500", message="接口禁用")
    
        user_name = xauth.current_name()
        part_file = True
        chunksize = 5 * 1024 * 1024
        chunk = xutils.get_argument_int("chunk")
        chunks = xutils.get_argument_int("chunks", 1)
        file = xutils.get_argument_field_storage("file")
        prefix = xutils.get_argument_str("prefix", "")
        dirname = xutils.get_argument_str("dirname", xconfig.DATA_DIR)
        dirname = dirname.replace("$DATA", xconfig.DATA_DIR)
        note_id = xutils.get_argument("note_id")

        # TODO 第一个部分上传的时候生成uuid文件名，并且记录映射关系
        # 第2次及以后上传的部分查找映射关系来定位到uuid文件名
        # 上传完成后删除映射关系

        # 不能访问上级目录
        if ".." in dirname:
            return webutil.FailedResult(code="fail", message="can not access parent directory")

        if not hasattr(file, "filename"):
            return webutil.FailedResult(code="400", message="请选择文件")
        
        if file.file is None:
            return webutil.FailedResult(code="400", message="file.file is None")
        if file.filename is None:
            return webutil.FailedResult(code="400", message="file.filename is None")

        filename = None
        webpath = ""
        origin_name = ""
        filepath = ""

        origin_name = file.filename
        fs_checker.check_file_name(origin_name)

        logging.info("upload filename=%s, length=%s", file.filename, file.length)
        
        fs_checker.check_upload_size(file.length)
        xutils.trace("UploadFile", file.filename)
        
        filename = os.path.basename(origin_name)
        filename = get_safe_file_name(filename)

        if dirname == "auto":
            filename = generate_filename(None, prefix)
            filepath, webpath = get_upload_file_path(
                user_name, filename, rename_conflict=True)
            dirname = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
        else:
            # check permission.
            if not xauth.is_admin():
                # 普通用户操作
                user_upload_dir = get_user_upload_dir(user_name)
                if not fsutil.is_parent_dir(user_upload_dir, dirname):
                    return webutil.FailedResult(code="403", message="无权操作")

            filepath = os.path.join(dirname, filename)
        
        if self.is_fixed_name(origin_name):
            filename = self.find_available_path(origin_name)
            filepath = os.path.join(dirname, filename)

        if os.path.exists(filepath):
            # return dict(code = "fail", message = "文件已存在")
            web.ctx.status = "500 Server Error"
            return webutil.FailedResult(code="fail", message="文件已存在")

        if part_file:
            tmp_name = "%s_%d.part" % (filename, chunk)
            seek = 0
        else:
            tmp_name = filename
            seek = chunk * chunksize

        xutils.makedirs(dirname)
        tmp_path = os.path.join(dirname, tmp_name)

        upload_size = seek
        with open(tmp_path, "wb") as fp:
            fp.seek(seek)
            if seek != 0:
                logging.info("seek to %s", seek)
            for file_chunk in file.file:
                upload_size += len(file_chunk)
                fs_checker.check_upload_size(upload_size)
                fp.write(file_chunk)
        
        if part_file and chunk+1 == chunks:
            self.merge_files(dirname, filename, chunks)

        try_fix_orientation(filepath)
        try_touch_note(note_id)

        if note_id != None and note_id != "":
            xutils.call("note.touch", note_id)

        result = webutil.SuccessResult()
        result.webpath=webpath
        result.link=get_link(origin_name, webpath)
        return result


class UploadSearchHandler:

    @xauth.login_required()
    def GET(self):
        key = xutils.get_argument_str("key")
        user_name = xauth.current_name_str()
        user_dir = os.path.join(xconfig.UPLOAD_DIR, user_name)

        find_key = "*" + key + "*"
        if find_key == "**":
            plist = []
        else:
            plist = sorted(xutils.search_path(user_dir, find_key, "file"))

        return xtemplate.render("fs/page/fs_upload.html",
                                show_aside=False,
                                html_title=T("文件"),
                                page="search",
                                pathlist=plist,
                                path=user_dir,
                                dirname=user_dir,
                                get_webpath=get_webpath,
                                upload_link_by_month=upload_link_by_month,
                                get_display_name=get_display_name)


class CheckHandler:

    @xauth.login_required()
    def GET(self):
        pass


xutils.register_func("fs.get_upload_file_path", get_upload_file_path)

xurls = (
    # 和文件系统的/fs/冲突了
    r"/fs_upload", UploadHandler,
    r"/fs_upload/check", CheckHandler,
    r"/fs_upload/search", UploadSearchHandler,
    r"/fs_upload/range", RangeUploadHandler
)
