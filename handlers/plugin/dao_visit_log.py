# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-01-29 12:21:04
@LastEditors  : xupingmao
@LastEditTime : 2023-01-29 12:33:22
@FilePath     : /xnote/handlers/plugin/dao_visit_log.py
@Description  : 描述
"""
import xutils
from xutils import dbutil
from xutils import dateutil
from xutils import Storage

_log_db = dbutil.get_table("plugin_visit_log")

def list_visit_logs(user_name, offset = 0, limit = -1):
    logs = _log_db.list(user_name = user_name, offset = offset, limit = limit, reverse = True)
    logs.sort(key = lambda x: x.time, reverse = True)
    return logs

def find_visit_log(user_name, url):
    log = _log_db.first_by_index("url", index_value = url, user_name=user_name)
    if log != None:
        return log

    for log in _log_db.iter(user_name = user_name, limit = -1):
        assert isinstance(log, Storage)
        if log.url == url:
            log.key = log._key
            return log
    return None

def update_visit_log(log, name):
    log.name = name
    log.time = dateutil.format_datetime()
    if log.visit_cnt is None:
        log.visit_cnt = 1
    log.visit_cnt += 1
    _log_db.update(log)


def delete_visit_log(user_name, name, url):
    exist_log = find_visit_log(user_name, url)
    if exist_log != None:
        _log_db.delete_by_key(exist_log.key, user_name)


def add_visit_log(user_name, url, name = "", args = ""):
    if user_name == None:
        user_name = "guest"
        
    exist_log = find_visit_log(user_name, url)
    if exist_log != None:
        exist_log.user = user_name
        update_visit_log(exist_log, name)
        return

    log = Storage()
    log.name = name
    log.url  = url
    log.args = args
    log.time = dateutil.format_datetime()
    log.user = user_name

    _log_db.insert_by_user(user_name, log)

xutils.register_func("plugin.add_visit_log", add_visit_log)