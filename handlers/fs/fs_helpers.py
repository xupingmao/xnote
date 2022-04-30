# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/27 16:07:55
# @modified 2022/04/09 10:54:40
# @filename fs_helpers.py

"""文件管理模块的工具
注: 叫fs_helpers是为了和fsutil名称混淆
"""

import xutils
import xconfig
import xauth
import xconfig
from xutils import dbutil
from xutils import FileItem, u, Storage, fsutil

_index_db = dbutil.get_hash_table("fs_index")


def get_index_db():
    return _index_db

def file_post_handler(item):
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
    return item

def handle_file_url(item):
    if item.type == "dir":
        item.url = "/fs/%s" % item.encoded_path
    elif xutils.is_img_file(item.path):
        item.url = "/fs/%s" % item.encoded_path
    elif xutils.is_audio_file(item.path):
        item.url = "/fs/%s" % item.encoded_path
    else:
        item.url = "/fs_view?path=%s" % item.encoded_path

FileItem.set_post_handler(file_post_handler)



def get_index_dirs():
    index_dirs = xauth.get_user_config("admin", "index_dirs")
    return index_dirs.split("\n")

def get_file_thumbnail(fpath):
    if xutils.is_img_file(fpath):
        return xutils.get_webpath(fpath)

    if xutils.is_text_file(fpath):
        return "/static/image/icon_txt.png"

    # 位置类型
    return "/static/image/file2.png"

def get_file_download_link(fpath):
    encode_path = xutils.encode_uri_component(fpath)
    download_link = "/fs/%s?type=blob" % encode_path
    return download_link

xutils.register_func("fs.get_file_thumbnail", get_file_thumbnail)
xutils.register_func("fs.get_file_download_link", get_file_download_link)
xutils.register_func("fs.get_index_dirs", get_index_dirs)
