# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-03-17 23:32:09
@LastEditors  : xupingmao
@LastEditTime : 2023-08-27 01:54:22
@FilePath     : /xnote/xutils/db/filters.py
@Description  : 描述
"""

_valid_op_set = set(["$prefix", "$contains"])

def check_complex_query(q: dict):
    for key in q:
        if key not in _valid_op_set:
            raise Exception("invalid query operator: %s" % key)

def create_func_by_where(where: dict, user_filter_func):
    def filter_func_complex(key, value):
        for query_key in where:
            query_val = where.get(query_key)
            attr_val = value.get(query_key)

            if isinstance(query_val, dict):
                # 前缀查询
                prefix = query_val.get("$prefix")
                if prefix != None:
                    if attr_val == None:
                        return False
                    if not attr_val.startswith(prefix):
                        return False
                    
                # 包含查询
                contains = query_val.get("$contains")
                if contains != None:
                    if attr_val == None:
                        return False
                    if attr_val.find(contains)<0:
                        return False
            else:
                if attr_val != query_val:
                    return False
        
        if user_filter_func != None:
            return user_filter_func(key, value)
        
        return True

    def filter_func(key, value):
        for query_key in where:
            query_val = where.get(query_key)
            attr_val = value.get(query_key)
            if attr_val != query_val:
                return False
        
        if user_filter_func != None:
            return user_filter_func(key, value)
        
        return True
    
    def empty_filter_func(key, value):
        if user_filter_func != None:
            return user_filter_func(key, value)
        return True

    has_complex_query = False
    for key in where:
        val = where.get(key)
        if isinstance(val, dict):
            has_complex_query = True
            check_complex_query(val)
    
    if has_complex_query:
        return filter_func_complex
    
    if len(where) == 0:
        return empty_filter_func
    
    return filter_func


