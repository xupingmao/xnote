# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2023/03/17 23:32:09
# @modified 2022/04/09 11:00:26
# @filename encode.py

def create_func_by_where(where: dict):
    def filter_func(key, value):
        for query_key in where:
            query_val = where.get(query_key)
            if value.get(query_key) != query_val:
                return False
        
        return True
    
    return filter_func


