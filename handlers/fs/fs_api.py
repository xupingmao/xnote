# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-22 00:17:06
@LastEditors  : xupingmao
@LastEditTime : 2024-05-19 17:20:25
@FilePath     : /xnote/handlers/fs/fs_api.py
@Description  : 文件API
"""

import os
import xutils
from xutils import webutil, dateutil, fsutil
from xnote.core import xauth

class FileConfigHandler:

    @xauth.login_required("admin")
    def POST(self):
        action = xutils.get_argument("action", "")

        if action == "sort":
            return self.update_sort()
        
        return dict(code = "error", message = "未知的action")

    def update_sort(self):
        order = xutils.get_argument("order", "")
        user_name = xauth.current_name()
        xauth.update_user_config(user_name, "fs_order", order)
        return dict(code = "success")


class FileDetailHandler:

    def get_user_name_by_uid(self, uid=0):
        try:
            import pwd
            user_info = pwd.getpwuid(uid)
            if user_info != None:
                return user_info.pw_name
        except:
            pass
        return f"uid({uid})"
        
    def get_group_name_by_gid(self, gid=0):
        try:
            import grp
            group_info = grp.getgrgid(gid)
            if group_info != None:
                return group_info.gr_name
        except:
            pass
        return f"gid({gid})"

    @xauth.login_required("admin")
    def GET(self):
        fpath = xutils.get_argument_str("fpath")
        try:
            basename = os.path.basename(fpath)
            display_name = xutils.decode_name(basename)
            stat = os.stat(fpath)
            detail_msg = ""
            detail_msg += f"文件路径: {fpath}"
            detail_msg += f"\n展示名称: {display_name}"
            detail_msg += f"\n修改时间: {dateutil.format_datetime(stat.st_mtime)}"
            detail_msg += f"\n变更时间: {dateutil.format_datetime(stat.st_ctime)}"
            detail_msg += f"\n访问时间: {dateutil.format_datetime(stat.st_atime)}"
            detail_msg += f"\n文件大小: {fsutil.format_size(stat.st_size)}"
            detail_msg += f"\n用户: {self.get_user_name_by_uid(stat.st_uid)}"
            detail_msg += f"\n用户组: {self.get_group_name_by_gid(stat.st_gid)}"
            return webutil.SuccessResult(data=detail_msg)
        except:
            xutils.print_exc()
            return webutil.FailedResult(code="500", message="读取文件信息失败")

xurls = (
    r"/fs_api/config", FileConfigHandler,
    r"/fs_api/detail", FileDetailHandler,
)