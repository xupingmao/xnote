# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-01-29 12:21:04
@LastEditors  : xupingmao
@LastEditTime : 2024-02-14 20:53:48
@FilePath     : /xnote/handlers/plugin/dao.py
@Description  : 描述
"""
import xutils
from xnote.core import xtables
from xnote.core import xauth
from xutils import dateutil
from xutils import Storage

class PageVisitLogDO(Storage):
    def __init__(self, **kw):
        self.user_id = 0
        self.url = ""
        self.args = ""
        self.visit_cnt = 0
        self.visit_time = dateutil.format_datetime()
        self.update(kw)

class PageVisitDao:
    
    db = xtables.get_table_by_name("page_visit_log")
    
    @classmethod
    def format_url(cls, url=""):
        return url[:256]
    
    @classmethod
    def create(cls, log: PageVisitLogDO):
        log.url = cls.format_url(log.url)
        return cls.db.insert(**log)
    
    @classmethod
    def find_one(cls, user_id=0, url=""):
        url = cls.format_url(url)
        result = cls.db.select_first(where = dict(user_id=user_id, url=url))
        if result != None:
            return PageVisitLogDO(**result)
        return None
    
    @classmethod
    def list_logs(cls, user_id=0, offset=0, limit=1000, order="visit_time desc"):
        results = []
        for item0 in cls.db.select(where=dict(user_id=user_id), offset=offset, limit=limit, order=order):
            item = PageVisitLogDO(**item0)
            results.append(item)
        return results
        
    
    @classmethod
    def update(cls, log: PageVisitLogDO):
        log.url = cls.format_url(log.url)
        return cls.db.update(where=dict(id=log.id), **log)
    
    @classmethod
    def delete_by_id(cls, log_id):
        return cls.db.delete(where=dict(id=log_id))
    
def list_visit_logs(user_name, offset = 0, limit = -1):
    user_id = xauth.UserDao.get_id_by_name(user_name)
    return PageVisitDao.list_logs(user_id=user_id, offset=offset, limit=limit, order="visit_time desc")

def delete_visit_log(user_name="", name="", url=""):
    user_id = xauth.UserDao.get_id_by_name(user_name)
    exist_log = PageVisitDao.find_one(user_id=user_id, url=url)
    if exist_log != None:
        PageVisitDao.delete_by_id(exist_log.id)


def add_visit_log(user_name="", url="", name = "", args = ""):
    if user_name == None:
        user_name = "guest"
        
    user_id = xauth.UserDao.get_id_by_name(user_name)
    
    exist_log = PageVisitDao.find_one(user_id=user_id, url=url)
    if exist_log != None:
        exist_log.visit_cnt += 1
        exist_log.visit_time = dateutil.format_datetime()
        PageVisitDao.update(exist_log)
        return

    log = PageVisitLogDO()
    log.user_id = user_id
    log.url  = url
    log.args = args
    log.visit_time = dateutil.format_datetime()
    log.visit_cnt = 1
    PageVisitDao.create(log)

xutils.register_func("plugin.add_visit_log", add_visit_log)