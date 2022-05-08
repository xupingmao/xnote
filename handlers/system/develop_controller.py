# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-06 12:40:55
@LastEditors  : xupingmao
@LastEditTime : 2022-05-06 12:45:28
@FilePath     : /xnote/handlers/system/develop_controller.py
@Description  : 开发者模块
"""

import xauth
import xtemplate

class DevelopHandler:

    @xauth.login_required("admin")
    def GET(self):
        return xtemplate.render("system/page/develop/index.html")


xurls = (
    r"/system/develop", DevelopHandler,
)
