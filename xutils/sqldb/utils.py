# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-02-15 21:19:48
@LastEditors  : xupingmao
@LastEditTime : 2024-02-15 21:39:31
@FilePath     : /xnote/xutils/sqldb/utils.py
@Description  : 描述
"""

def safe_str(obj, max_length=-1):
    if obj == None:
        return ""
    value = str(obj)
    if max_length > 0:
        return value[:max_length]
    return value

    
