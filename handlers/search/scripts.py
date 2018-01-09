# encoding=utf-8
# Created by xupingmao on 2017/06/14
import os
import six
import xconfig
import xutils
import xauth
from xutils import SearchResult

def search(ctx, name):
    if not xauth.is_admin():
        return None
    results = []
    for fname in xutils.listdir(xconfig.SCRIPTS_DIR):
        if name in fname:
            result = xutils.SearchResult()
            result.name = xutils.u("脚本 - ") + fname
            result.raw  = xutils.u("搜索到可执行脚本 - ") + fname
            result.url  = xutils.u("/system/script_admin?op=edit&name=%s") % fname
            result.command = xutils.u("/system/script_admin/execute?name=%s") % fname
            results.append(result)
    # 图书搜索结果
    bookspath = os.path.join(xconfig.DATA_DIR, "books")
    pathlist = xutils.search_path(bookspath, "*" + name + "*")
    if len(pathlist) > 0:
        url = "/fs_find?path=%s&find_key=%s"%(bookspath,name)
        results.append(SearchResult("图书搜索结果(%s) - %s" % (len(pathlist), name), url))
    return results