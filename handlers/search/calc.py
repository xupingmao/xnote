# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""Description here"""
import re
import xmanager
import xutils

SearchResult = xutils.SearchResult

def safe_check(expression):
    p = re.compile(r"^[.0-9+\-*\/% \(\)\~]*\Z")
    m = p.match(expression)
    # print(m.group())
    if m.group():
        return m.group()
    return None

def do_calc(expression):
    if expression.startswith("calc"):
        expression = expression[4:]
    expression = expression.strip()
    exp = safe_check(expression)
    if exp is None:
        return
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

# xmanager.register_search_func(r"calc(.*)", do_calc)
# xmanager.register_search_func(r"(.*[0-9]+.*)", try_calc)