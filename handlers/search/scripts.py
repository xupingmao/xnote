# encoding=utf-8
# Created by xupingmao on 2017/06/14
import os
import six
import xconfig
import xutils
import xauth
import xmanager
from xutils import SearchResult
from xutils import u

def search_plugins(name):
    results = []
    for fname in xutils.listdir(xconfig.PLUGINS_DIR):
        if name in fname:
            result = SearchResult()
            result.name = u("Plugins - " + fname)
            result.url  = u("/plugins/" + fname)
            results.append(result)
    return results

def search(ctx, name):
    if not xauth.is_admin():
        return None
    if not ctx.search_tool:
        return
    results = search_plugins(name)
    for fname in xutils.listdir(xconfig.SCRIPTS_DIR):
        fpath = os.path.join(xconfig.SCRIPTS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        if name in fname:
            result = xutils.SearchResult()
            result.name = xutils.u("脚本 - ") + fname
            result.raw  = xutils.u("搜索到可执行脚本 - ") + fname
            result.url  = xutils.u("/system/script_admin?op=edit&name=%s") % fname
            result.command = xutils.u("/system/script_admin/execute?name=%s") % fname
            results.append(result)
    return results


@xmanager.listen("search")
@xutils.timeit(logfile=True, name="search books")
def search_books(ctx):
    if not xauth.is_admin():
        return
    if not ctx.category == "book":
        return
    name = ctx.input_text
    # 图书搜索结果
    bookspath = os.path.join(xconfig.DATA_DIR, "books")
    pathlist = xutils.search_path(bookspath, "*" + name + "*")
    if len(pathlist) > 0:
        url = "/fs_find?path=%s&find_key=%s"%(bookspath,name)
        ctx.tools.append(SearchResult("图书搜索结果(%s) - %s" % (len(pathlist), name), url))