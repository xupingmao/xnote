# encoding=utf-8
# Created by xupingmao on 2017/06/14
import os
import six
import xconfig
import xutils
import xauth
import xmanager
from xutils import SearchResult, u, textutil

def search_plugins(name):
    results = []
    dirname = xconfig.PLUGINS_DIR
    words   = textutil.split_words(name)
    for fname in xutils.listdir(dirname):
        unquote_name = xutils.unquote(fname)
        if textutil.contains_all(unquote_name, words):
            result           = SearchResult()
            result.category  = "plugin"
            result.name      = u("插件 - " + unquote_name)
            result.url       = u("/plugins/" + fname)
            result.edit_link = u("/code/edit?path=" + os.path.join(dirname, fname))
            results.append(result)
    return results

def search_scripts(name):
    results = []
    for fname in xutils.listdir(xconfig.SCRIPTS_DIR):
        fpath = os.path.join(xconfig.SCRIPTS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        if fname.endswith(".zip"):
            continue
        if name in fname:
            result         = xutils.SearchResult()
            result.name    = xutils.u("脚本 - ") + fname
            result.raw     = xutils.u("搜索到可执行脚本 - ") + fname
            result.url     = xutils.u("/system/script_admin?op=edit&name=%s") % fname
            result.command = xutils.u("/system/script_admin/execute?name=%s") % fname
            results.append(result)
    return results

@xmanager.listen("search")
def on_search_scripts(ctx):
    if not xauth.is_admin():
        return None
    if not ctx.search_tool:
        return
    name    = ctx.key
    results = search_plugins(name)
    results += search_scripts(name)
    ctx.tools += results


@xmanager.listen("search")
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

