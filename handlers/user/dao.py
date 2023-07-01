# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-07-01 15:58:30
@LastEditors  : xupingmao
@LastEditTime : 2023-07-01 16:30:39
@FilePath     : /xnote/handlers/user/dao.py
@Description  : 用户的DAO对象
"""

import enum
from xutils import dateutil, dbutil, Storage

class UserOpTypeEnum(enum.Enum):
    # 登录
    login = "login"
    
    # 修改密码
    change_password = "change_password"

    # 管理员重置密码
    reset_password = "reset_password"

class UserOpLog(Storage):

    def __init__(self):
        self.ctime = dateutil.format_datetime()
        self.user_name = ""
        self.type = ""
        self.detail = ""
        self.ip = ""

class UserOpLogDao:

    @classmethod
    def init(cls):
        cls.db = dbutil.get_table("user_op_log")
        cls.max_log_size = 500

    @classmethod
    def create_op_log(cls, op_log):
        assert isinstance(op_log, UserOpLog)
        assert op_log.user_name != ""
        cls.db.insert(op_log)
        if cls.db.count_by_user(op_log.user_name) > cls.max_log_size:
            for item in cls.db.list_by_user(op_log.user_name, limit=20):
                cls.db.delete(item)


UserOpLogDao.init()
