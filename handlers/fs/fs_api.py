# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-22 00:17:06
@LastEditors  : xupingmao
@LastEditTime : 2022-05-22 00:20:57
@FilePath     : /xnote/handlers/fs/fs_api.py
@Description  : 文件API
"""

import xutils
import xauth

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

xurls = (
    r"/fs_api/config", FileConfigHandler
)