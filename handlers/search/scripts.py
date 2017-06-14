# encoding=utf-8
# Created by xupingmao on 2017/06/14
import os
import xconfig
import xutils
import xauth

def search(name):
    if not xauth.is_admin():
        return None
    results = []
    for fname in os.listdir(xconfig.SCRIPTS_DIR):
        if name in fname:
            result = xutils.SearchResult()
            result.name = "脚本 - " + fname
            result.raw  = "搜索到可执行脚本 - " + fname
            result.url  = "/system/script_admin?op=edit&name=%s" % fname
            result.command = "/system/script_admin/execute?name=%s" % fname
            results.append(result)
    return results