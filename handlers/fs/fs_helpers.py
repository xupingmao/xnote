# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/27 16:07:55
# @modified 2022/02/27 16:20:06
# @filename fs_helpers.py

"""文件管理模块的工具"""

import xutils
import xconfig
from xutils import FileItem, u, Storage, fsutil

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
