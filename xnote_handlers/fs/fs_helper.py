# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/27 16:07:55
# @modified 2022/04/09 10:54:40
# @filename fs_helpers.py

"""文件管理模块的工具
注: 叫fs_helpers是为了和fsutil名称混淆
"""

import os
import xutils
import typing

from typing import List
from xnote.core import xconfig
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xtables
from xutils import dbutil
from xutils import format_size
from xutils import fsutil, textutil
from xutils.dbutil import LdbTable
from xutils.fsutil import FileItem
from xutils.sqldb import TableProxy
from xutils import Storage, BaseDataRecord
from xnote.service.system_meta_service import SystemMetaEnum
from .fs_models import FileInfoRecord, FileInfo
from .fs_dao import FileInfoDao

def get_index_db(): # type: ()-> TableProxy
    return FileInfoDao.db

def handle_file_item(item: fsutil.FileItem):
    """文件的后置处理器"""
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

    handle_file_url(item)
    item.show_opt_btn = True
    return item

def handle_file_url(item: fsutil.FileItem):
    if item.custom_url:
        item.url = item.custom_url
        item.data_url = item.custom_url
        return
    
    item.css_class = ""
    server_home = xconfig.WebConfig.server_home
    if item.type == "dir":
        item.url = server_home + "/fs/~%s" % item.encoded_path
    elif xutils.is_img_file(item.path):
        item.url = "javascript:void(0)"
        item.css_class = "x-photo"
    elif xutils.is_audio_file(item.path):
        item.url = server_home + "/fs/~%s" % item.encoded_path
    else:
        item.url = server_home + "/fs_preview?path=%s&embed=false" % item.encoded_path
    
    item.data_url = server_home + "/fs/~" + item.encoded_path

def get_parent_file_object(path: str, name = ""):
    path = os.path.abspath(path)
    parent_file = FileItem(os.path.dirname(path))
    handle_file_item(parent_file)
    if name != "":
        parent_file.name = name
    parent_file.show_opt_btn = False
    return parent_file

def get_index_dirs():
    admin_user_id = xauth.UserDao.get_id_by_name("admin")
    index_dirs = xauth.get_user_config(admin_user_id, "fs_index_dirs")
    assert isinstance(index_dirs, str)
    return index_dirs.split("\n")

def get_file_thumbnail(fpath):
    if xutils.is_img_file(fpath):
        return xutils.get_webpath(fpath) + "?mode=thumbnail"

    if xutils.is_text_file(fpath):
        return "/_static/image/icon_txt.png"

    # 未知类型
    return "/_static/image/file2.png"

def get_file_download_link(fpath:str):
    if fsutil.is_parent_dir(xconfig.DATA_DIR, fpath):
        relative_path = fsutil.get_relative_path(fpath, xconfig.DATA_DIR)
        fpath = relative_path
        encoded_path = xutils.encode_uri_component(fpath)
        return "/data/%s?type=blob" % encoded_path
    encoded_path = xutils.encode_uri_component(fpath)
    download_link = "/fs/%s?type=blob" % encoded_path
    return download_link


def sort_files_by_size(filelist: typing.List[FileItem]):
    for file in filelist:
        fpath = file.path
        fpath = os.path.abspath(fpath)
        realpath = os.path.realpath(fpath)
        info = FileInfoDao.get_by_fpath(realpath)
        if info != None and hasattr(info, "fsize"):
            file.fsize = info.fsize
            size_str = format_size(info.fsize)
            if os.path.islink(fpath):
                file.size = "Link(%s)" % size_str
            else:
                file.size = size_str
        else:
            file.size = "Unknown"

    def key_func(file):
        if not isinstance(file.fsize, int):
            return 0
        return file.fsize

    filelist.sort(key = key_func, reverse = True)

def sort_files(filelist: List[FileItem]):
    def file_item_key_func(item: FileItem):
        if item.type == "dir":
            return f"0-{item.name}"
        return f"1-{item.name}"
    
    filelist.sort(key=file_item_key_func)


def is_hidden_file(item: FileItem):
    if not SystemMetaEnum.fs_hide_files.bool_value:
        return
    
    if item.name.startswith("."):
        return True
    
    return item.name.endswith((".class", ".pyc"))

def get_fs_url(fpath: str, include_server_home=True):
    fpath = fpath.replace("\\","/")
    encoded_path = textutil.encode_uri_component(fpath)
    if include_server_home:
        return f"{xconfig.WebConfig.server_home}/fs/~{encoded_path}"
    else:
        return f"/fs/~{encoded_path}"


xutils.register_func("fs.get_file_thumbnail", get_file_thumbnail)
xutils.register_func("fs.get_file_download_link", get_file_download_link)
xutils.register_func("fs.get_index_dirs", get_index_dirs)


