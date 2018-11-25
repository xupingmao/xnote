# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/04/29 20:09:51
# @modified 2018/11/25 20:05:40
import xutils
import xtemplate
import xtables
import xauth
from xutils import Storage

class StorageHandler:

    @xauth.login_required()
    def GET(self):
        key  = xutils.get_argument("key")
        db = xtables.get_storage_table()
        config = db.select_one(where=dict(key=key, user=xauth.get_current_name()))
        if config is None:
            config = Storage(key=key, value="")
        return xtemplate.render("system/storage.html", 
            show_aside = False,
            config = config)
    
    @xauth.login_required()
    def POST(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")
        user = xauth.get_current_name()
        db = xtables.get_storage_table()
        config = db.select_one(where=dict(key=key, user=user))
        if config is None:
            db.insert(user = user, key = key, value = value, 
                ctime = xutils.format_datetime(), 
                mtime = xutils.format_datetime())
        else:
            db.update(value=value, mtime = xutils.format_datetime(), where=dict(key=key, user=user))

        config = Storage(key = key, value = value)
        return xtemplate.render("system/storage.html", 
            show_aside = False,
            config = config)

xurls = (
    r"/system/storage", StorageHandler
)