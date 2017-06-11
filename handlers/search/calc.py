# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""Description here"""
import xmanager
import xutils

SearchResult = xutils.SearchResult

def do_calc(expression):
    exp = expression
    try:
        value = eval(exp)
        f = SearchResult()
        f.url = "#"
        f.name = "计算结果"
        f.raw = str(value)
        return [f]
    except Exception as e:
        print(e)
        return []

def try_calc(expression):
    exp = expression
    try:
        value = eval(exp)
        f = SearchResult()
        f.name = "计算结果"
        f.raw = str(value)
        return [f]
    except Exception as e:
        print(e)
        return []

def handle_calc(expression):
    print(expression)
    return []

# xmanager.register_search_func(r"calc(.*)", do_calc)
# xmanager.register_search_func(r"(.*[0-9]+.*)", try_calc)