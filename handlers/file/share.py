# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/12
# 

"""Description here"""

import os
import time
import web
import xtables
import xutils
import xconfig
import xauth

from . import dao

class handler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", type=int)
        db = xtables.get_file_table()
        db.update(groups="*", where=dict(id=id, creator=xauth.get_current_name()))
        raise web.seeother("/file/view?id=%s"%id)

    def GET_old(self):
        id = xutils.get_argument("id", type = int)
        file = dao.get_by_id(id)
        random_file_name = str(time.time()) + ".md"
        random_file_path = os.path.join(xconfig.TMP_DIR, random_file_name)
        with open(random_file_path, "w", encoding="utf-8") as fp:
            fp.write(file.content)
        raise web.seeother("/tmp/" + random_file_name)

class UnshareHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", type=int)
        db = xtables.get_file_table()
        db.update(groups=xauth.get_current_name(), 
            where=dict(id=id, creator=xauth.get_current_name()))
        raise web.seeother("/file/view?id=%s"%id)

xurls = (
    r"/file/share", handler,
    r"/file/share/cancel", UnshareHandler
)