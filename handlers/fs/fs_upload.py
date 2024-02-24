# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2017
# @modified 2021/07/31 14:27:13
import os
import web
import logging
from xnote.core import xauth
from xnote.core import xconfig
import xutils
from xnote.core import xtemplate
from xnote.core import xmanager
import time
import math
from xutils import fsutil, Storage, dateutil
from xnote.core.xtemplate import T
from xnote.core.xnote_event import FileUploadEvent
from .fs_helper import FileInfoDao
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


def get_safe_file_name(filename):
    """处理文件名中的特殊符号"""
    for c in " @$:#\\|=&?":
        filename = filename.replace(c, "_")
    return filename


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


def try_lock_file(fpath):
    return True

def try_fix_orientation(fpath):
    fix_orientation = xutils.get_argument("fix_orientation", "")
    # print("fix_orientation", fix_orientation)
    if fix_orientation != "true":
        return

    if Image == None:
        # 没有安装PIL
        return

    name, ext = os.path.splitext(fpath)
    if ext.lower() not in (".jpg", ".jpeg"):
        return

    tmp_path = fsutil.tmp_path(xutils.create_uuid())
    os.rename(fpath, tmp_path)

    with Image.open(tmp_path) as img:
        exif = img.getexif()
        # print("exif", exif)
        orientation = exif.get(TAG_ORIENTATION)

        if orientation in (3, 6):
            print("fix orientation")
            img_new = img.copy()
            exif_new = img_new.getexif()
            exif_new[TAG_ORIENTATION] = 1
            img_new.save(fpath)
            img_new.close()
            os.remove(tmp_path)
        else:
            # 重新命名回去
            os.rename(tmp_path, fpath)

# 业务上用到的函数

def get_user_upload_dir(user):
    return os.path.join(xconfig.UPLOAD_DIR, user)

def get_upload_file_path(user, filename, upload_dir="files", rename_conflict=False):
    """生成上传文件名"""
    from xnote.core import xconfig
    if xconfig.USE_URLENCODE:
        filename = xutils.quote_unicode(filename)
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

    @xauth.login_required()
    def POST(self):
        file = xutils.get_argument_field_storage("file")
        prefix = xutils.get_argument_str("prefix")
        name = xutils.get_argument_str("name")
        note_id = xutils.get_argument_str("note_id")
        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name
        webpath = ""
        filename = ""

        if file.filename != None:            
            filename = get_safe_file_name(file.filename)
            if file.filename == "":
                return dict(code="400", message="filename is empty")
            
            basename, ext = os.path.splitext(filename)
            if name == "auto":
                # iOS上传文件截图文件固定是image.png
                filename = generate_filename(None, prefix, ext)

            filepath, webpath = get_upload_file_path(user_name, filename)

            with open(filepath, "wb") as fout:
                for chunk in file.file:
                    fout.write(chunk)
            
            event = FileUploadEvent()
            event.fpath = filepath
            event.user_name = user_info.name
            event.user_id = user_info.id
            xmanager.fire("fs.upload", event)

            try_fix_orientation(filepath)
            try_touch_note(note_id)

        return dict(code="success", webpath=webpath, link=get_link(filename, webpath))

    @xauth.login_required()
    def GET(self):
        return self.get_upload_page_v1()
        
    def get_upload_page_v1(self):
        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name
        xmanager.add_visit_log(user_name, "/fs_upload")

        year = xutils.get_argument_str("year", time.strftime("%Y"))
        month = xutils.get_argument_str("month", time.strftime("%m"))
        if len(month) == 1:
            month = '0' + month
        

        dirname = os.path.join(xconfig.FileConfig.data_dir, "files",
                               user_name, "upload", year, month)
        pathlist = fsutil.listdir_abs(dirname)
        
        return xtemplate.render("fs/page/fs_upload.html",
                                show_aside=False,
                                html_title=T("文件"),
                                pathlist=pathlist,
                                year=int(year),
                                month=int(month),
                                path=dirname,
                                dirname=dirname,
                                get_webpath=get_webpath,
                                upload_link_by_month=upload_link_by_month,
                                get_display_name=get_display_name)

    def get_upload_page_v2(self):
        # TODO 基于数据库数据的上传页面
        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name
        xmanager.add_visit_log(user_name, "/fs_upload")

        user_id = user_info.id
        files = FileInfoDao.list(user_id=user_id, limit=50)
        
        kw = Storage()
        kw.html_title = T("文件")
        kw.files = files
        
        return xtemplate.render("fs/page/fs_upload_v2.html",**kw)
    

class RangeUploadHandler:

    def merge_files(self, dirname, filename, chunks):
        dest_path = os.path.join(dirname, filename)
        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name

        with open(dest_path, "wb") as fp:
            for chunk in range(chunks):
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

    @xauth.login_required()
    def POST(self):
        user_name = xauth.current_name()
        part_file = True
        chunksize = 5 * 1024 * 1024
        chunk = xutils.get_argument_int("chunk")
        chunks = xutils.get_argument("chunks", 1, type=int)
        file = xutils.get_argument_field_storage("file")
        prefix = xutils.get_argument_str("prefix", "")
        dirname = xutils.get_argument_str("dirname", xconfig.DATA_DIR)
        dirname = dirname.replace("$DATA", xconfig.DATA_DIR)
        note_id = xutils.get_argument("note_id")

        # 不能访问上级目录
        if ".." in dirname:
            return dict(code="fail", message="can not access parent directory")

        filename = None
        webpath = ""
        origin_name = ""
        filepath = ""

        if hasattr(file, "filename"):
            origin_name = file.filename
            xutils.trace("UploadFile", file.filename)
            filename = os.path.basename(file.filename)
            filename = get_safe_file_name(filename)
            filename = xutils.get_real_path(filename)
            if dirname == "auto":
                filename = generate_filename(None, prefix)
                filepath, webpath = get_upload_file_path(
                    user_name, filename, rename_conflict=True)
                dirname = os.path.dirname(filepath)
                filename = os.path.basename(filepath)
            else:
                # check permission.
                if xauth.current_role() != "admin":
                    # 普通用户操作
                    user_upload_dir = get_user_upload_dir(user_name)
                    if not fsutil.is_parent_dir(user_upload_dir, dirname):
                        return dict(code="403", message="无权操作")

                filepath = os.path.join(dirname, filename)
            
            if self.is_fixed_name(origin_name):
                filename = self.find_available_path(origin_name)
                filepath = os.path.join(dirname, filename)

            if chunk == 0:
                lock = try_lock_file(filepath)

            if os.path.exists(filepath):
                # return dict(code = "fail", message = "文件已存在")
                web.ctx.status = "500 Server Error"
                return dict(code="fail", message="文件已存在")

            if part_file:
                tmp_name = "%s_%d.part" % (filename, chunk)
                seek = 0
            else:
                tmp_name = filename
                seek = chunk * chunksize

            xutils.makedirs(dirname)
            tmp_path = os.path.join(dirname, tmp_name)

            with open(tmp_path, "wb") as fp:
                fp.seek(seek)
                if seek != 0:
                    logging.info("seek to %s", seek)
                for file_chunk in file.file:
                    fp.write(file_chunk)
        else:
            return dict(code="fail", message=u"请选择文件")
        if part_file and chunk+1 == chunks:
            self.merge_files(dirname, filename, chunks)

        try_fix_orientation(filepath)
        try_touch_note(note_id)

        if note_id != None and note_id != "":
            xutils.call("note.touch", note_id)
        return dict(code="success", webpath=webpath, link=get_link(origin_name, webpath))


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
