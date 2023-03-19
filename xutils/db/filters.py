# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-03-17 23:32:09
@LastEditors  : xupingmao
@LastEditTime : 2023-03-19 15:50:59
@FilePath     : /xnote/xutils/db/filters.py
@Description  : 描述
"""

def create_func_by_where(where: dict, user_filter_func):
    def filter_func_with_prefix(key, value):
        for query_key in where:
            query_val = where.get(query_key)
            attr_val = value.get(query_key)

            if isinstance(query_val, dict):
                prefix = query_val.get("$prefix")
                if prefix != None:
                    if attr_val == None:
                        return False
                    if not attr_val.startswith(prefix):
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

    has_prefix_query = False
    for key in where:
        val = where.get(key)
        if isinstance(val, dict):
            has_prefix_query = True
    
    if has_prefix_query:
        return filter_func_with_prefix
    
    return filter_func


