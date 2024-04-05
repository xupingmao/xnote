# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-04-05 11:56:40
@LastEditors  : xupingmao
@LastEditTime : 2024-04-05 12:04:59
@FilePath     : /xnote/xutils/sqldb/table_config.py
@Description  : SQL表配置
"""

class TableConfig:

    log_profile = False
    enable_binlog = False
    enable_auto_ddl = True # 自动DDL
    
    _disable_profile_tables = set()
    _disable_binlog_tables = set()
    
    @classmethod
    def disable_profile(cls, table_name=""):
        cls._disable_profile_tables.add(table_name)
        
    @classmethod
    def disable_binlog(cls, table_name=""):
        cls._disable_binlog_tables.add(table_name)
    
