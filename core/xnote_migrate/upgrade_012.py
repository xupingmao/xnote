# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-05-20 22:54:35
@LastEditors  : xupingmao
@LastEditTime : 2023-05-22 00:04:16
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

        if item.login_time != None:
            user_info.login_time = item.login_time

        if item.mtime != None:
            user_info.mtime = item.mtime
        
        if item.ctime != None:
            user_info.ctime = item.mtime

        record = xauth.UserModel.get_by_name(item.name)
        if record == None:
            xauth.UserModel.create(user_info)
        else:
            record.update(user_info)
            xauth.UserModel.update(record)