# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/06/26 21:45:27
# @modified 2021/06/26 23:05:53
# @filename fs_func.py
import xutils
from xutils import fsutil

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