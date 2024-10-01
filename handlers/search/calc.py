# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2021/07/18 17:57:33
import re
import xutils
from xnote.core import xmanager
from xutils import Storage
from xutils import SearchResult
from xnote.core.models import SearchContext

def safe_check(expression):
    p = re.compile(r"^[.0-9+\-*\/% \(\)\~]*\Z")
    m = p.match(expression)
    # print(m.group())
    if m is not None and m.group():
        return m.group()
    return None

@xmanager.searchable(r"(.*[0-9]+.*)")
def do_calc(ctx: SearchContext):
    expression = ctx.key
    if expression.startswith("calc"):
        expression = expression[4:]
    expression = expression.strip()
    exp = safe_check(expression)
    if exp is None:
        return
    try:
        value = eval(exp)
        if str(value) == exp:
            return
        f = SearchResult()
        f.url = "#"
        f.name = "计算结果"
        f.icon = "fa-calculator"
        f.raw = "{expression}={value}".format(**locals())
        ctx.tools.append(f)
    except Exception as e:
        xutils.print_exc()

