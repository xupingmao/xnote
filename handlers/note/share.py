# -*- coding:utf-8 -*-  
# @author xupingmao
# @since 2017/05/12
# @modified 2018/02/10 13:17:27

"""Description here"""

import os
import time
import web
import xtables
import xutils
import xconfig
import xauth

class handler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", type=int)
        db = xtables.get_file_table()
        db.update(is_public=1, where=dict(id=id, creator=xauth.get_current_name()))
        raise web.seeother("/file/view?id=%s"%id)


class UnshareHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", type=int)
        db = xtables.get_file_table()
        db.update(is_public=0, 
            where=dict(id=id, creator=xauth.get_current_name()))
        raise web.seeother("/file/view?id=%s"%id)

xurls = (
    r"/file/share", handler,
    r"/file/share/cancel", UnshareHandler
)