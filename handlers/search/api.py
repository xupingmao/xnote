# encoding=utf-8
# Created by xupingmao on 2017/06/18
# @modified 2018/11/11 17:59:26
from __future__ import print_function
import os
import xutils
from xnote.core import xconfig
from xnote.core import xauth
from xnote.core.models import SearchContext
from xutils import six

SearchResult = xutils.SearchResult
ROOT_PATH = os.path.join(xconfig.HANDLERS_DIR, "api")

# 定时任务别名
_api_name_dict = {
    "天气预报": "report_weather",
    "闹钟": "alarm",
}


def init_name_dict():
    global _api_name_dict
    for fname in os.listdir(ROOT_PATH):
        if fname[0] == '_':
            continue
        fpath = os.path.join(ROOT_PATH, fname)
        name, ext = os.path.splitext(fname)
        if os.path.isfile(fpath) and ext == ".py":
            _api_name_dict[name] = name

init_name_dict()

def search(ctx: SearchContext, name):
    global _api_name_dict
    if not xauth.is_admin():
        return
    if not ctx.search_tool:
        return
    results = []
    for task_name in _api_name_dict:
        task_command = _api_name_dict[task_name]
        # print(name, task_name)
        if name in task_name:
            result = SearchResult()
            result.name = f"系统接口 - {name}"
            result.command = f"/api/{task_command}"
            result.url = result.command
            results.append(result)
    return results
