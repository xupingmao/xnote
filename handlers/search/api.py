# encoding=utf-8
# Created by xupingmao on 2017/06/18
import os
import xutils
import xconfig

SearchResult = xutils.SearchResult
ROOT_PATH = os.path.join(xconfig.HANDLERS_DIR, "api")

# 定时任务别名
_task_name_dict = {
    "天气预报": "report_weather"
}


def init_name_dict():
    global _task_name_dict
    for fname in os.listdir(ROOT_PATH):
        fpath = os.path.join(ROOT_PATH, fname)
        name, ext = os.path.splitext(fname)
        if os.path.isfile(fpath) and ext == ".py":
            _task_name_dict[name] = name

init_name_dict()

def search(name):
    global _task_name_dict
    results = []
    for task_name in _task_name_dict:
        task_command = _task_name_dict[task_name]
        if name in task_name:
            result = SearchResult()
            result.name = "系统接口 - " + task_name
            result.command = "/api/%s" % task_command
            results.append(result)
    return results
