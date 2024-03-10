# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 15:34:47
@LastEditors  : xupingmao
@LastEditTime : 2024-03-10 16:01:25
@FilePath     : /xnote/xnote/service/service_job.py
@Description  : 描述
"""

from xnote.core import xtables
from xutils import dateutil

class JobStatusEnum:
    """枚举无法扩展,所以这里不用,从外部添加枚举值可以直接设置新的属性"""
    init = 0 # 初始化
    processing = 1 # 执行中
    success = 2  # 执行成功
    failed = 3 # 执行失败
    
    @classmethod
    def get_title_by_status(cls, status=0):
        if status == cls.init:
            return "初始化"
        if status == cls.processing:
            return "执行中"
        if status == cls.success:
            return "执行成功"
        if status == cls.failed:
            return "执行失败"
        return str(status)
    
class SysJob:
    def __init__(self):
        self.id = 0
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.job_status = JobStatusEnum.init
        self.job_type = ""
        self.job_params = ""
        self.job_result = ""

class JobManager:
    """Database transaction."""

    def __init__(self, job_info):
        assert isinstance(job_info, SysJob)
        self.job_info = job_info

    def __enter__(self):
        JobService.create_job(self.job_info)
        return self

    def __exit__(self, exctype, excvalue, traceback):
        if exctype is not None:
            self.job_info.job_status = JobStatusEnum.failed
        else:
            self.job_info.job_status = JobStatusEnum.success
        
        JobService.update_job(self.job_info)


class JobService:
    
    db = xtables.get_table_by_name("sys_job")
    
    @classmethod
    def create_job(cls, job_info):
        assert isinstance(job_info, SysJob)
        assert job_info.id == 0
        
        record = job_info.__dict__
        record.pop("id", None)
        
        db_id = cls.db.insert(record)
        job_info.id = db_id
        return db_id
    
    @classmethod
    def get_job_by_id(cls, job_id=0):
        record = cls.db.select_first(where=dict(id=job_id))
        if record != None:
            return cls.dict_to_obj(record)
        return None
    
    @classmethod
    def delete_by_id(cls, job_id=0):
        return cls.db.delete(where=dict(id=job_id))
    
    @classmethod
    def dict_to_obj(cls, record):
        job_info = SysJob()
        job_info.__dict__.update(record)
        return job_info
    
    @classmethod
    def list_job_page(cls, job_status_list=[], offset=0, limit=20, order="ctime desc"):
        where_sql = "1=1"
        if len(job_status_list) > 0:
            where_sql += "AND job_status IN $job_status_list"
        
        vars = dict(job_status_list=job_status_list)
        records = cls.db.select(where=where_sql, vars=vars, offset=offset, limit=limit, order=order)
        result = []
        for record in records:
            result.append(cls.dict_to_obj(record))
        amount = cls.db.count(where=where_sql, vars=vars)
        return result, amount
    
    @classmethod
    def update_job(cls, job_info):
        assert isinstance(job_info, SysJob)
        
        updates = job_info.__dict__
        return cls.db.update(where=dict(id=job_info.id), **updates)
    
    @classmethod
    def run_with_job(cls, job_info):
        assert isinstance(job_info, SysJob)
        return JobManager(job_info=job_info)
        