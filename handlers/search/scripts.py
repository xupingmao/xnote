# encoding=utf-8
# Created by xupingmao on 2017/06/14
# @modified 2021/04/24 21:33:47
import os
import xconfig
import xutils
import xauth
import xmanager
from xutils import SearchResult, textutil

def search_scripts(name):
    words   = textutil.split_words(name)
    results = []
    for fname in xutils.listdir(xconfig.SCRIPTS_DIR):
        fpath = os.path.join(xconfig.SCRIPTS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        if fname.endswith(".zip"):
            continue
        if textutil.contains_all(fname, words):
            result         = xutils.SearchResult()
            result.icon    = "icon-script"
            result.name    = xutils.u(fname)
            result.raw     = xutils.u("搜索到可执行脚本 - ") + fname
            result.url     = xutils.u("/code/edit?path=%s") % fpath
            result.command = xutils.u("/system/script_admin/execute?name=%s") % fname
            results.append(result)
    return results

# 脚本工具比较危险，不允许执行了
# @xmanager.searchable()
def on_search_scripts(ctx):
    if not xauth.is_admin():
        return None
    if not ctx.search_tool:
        return
    if ctx.search_dict:
        return
    name    = ctx.key
    ctx.commands += search_scripts(name)


@xmanager.searchable()
def on_search_books(ctx):
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

