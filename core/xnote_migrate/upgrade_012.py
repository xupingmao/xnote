# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-05-20 22:54:35
@LastEditors  : xupingmao
@LastEditTime : 2023-05-20 23:28:07
@FilePath     : /xnote/core/xnote_migrate/upgrade_012.py
@Description  : 描述
"""

from xutils import dbutil, dateutil, Storage
from . import base
import xauth


def do_upgrade():
    base.execute_upgrade("012.1", migrate_user_20230520)

def migrate_user_20230520():
    old_db = dbutil.get_table("user")

    for item in old_db.iter(limit=-1):
        user_info = Storage()

        user_info.name = item.name
        user_info.password = item.password
        user_info.salt = item.salt
        user_info.ctime = item.ctime
        user_info.mtime = item.mtime
        user_info.token = item.token
        user_info.login_time = item.login_time

        if user_info.mtime == None:
            user_info.mtime = dateutil.format_datetime()
        
        if user_info.ctime == None:
            user_info.ctime = user_info.mtime

        record = xauth.UserModel.get_by_name(item.name)
        if record == None:
            xauth.UserModel.create(user_info)
        else:
            record.update(user_info)
            xauth.UserModel.update(record)