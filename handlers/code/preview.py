# encoding=utf-8
# @modified 2019/09/30 11:13:34
import os
import web
import xutils
import xtemplate
import xconfig
import xauth
from xtemplate import render
from xutils import Storage
from xutils import fsutil

WIKI_PATH = "./"

HIDE_EXT_LIST = [
    ".bak"
]

def check_resource(path):
    if xutils.is_img_file(path):
        if fsutil.is_parent_dir("./docs", path):
            relative_path = fsutil.get_relative_path(path, "./docs")
            raise web.seeother("/fs_doc?fpath=%s" % xutils.encode_uri_component(relative_path))

        uri = "/fs_get?fpath=%s" % xutils.b64encode(path)
        raise web.seeother(uri)
    return False


class FileItem:

    def __init__(self, parent, name, currentdir):
        if parent.endswith("/"):
            self.path = parent + name
        else:
            self.path = parent + "/" + name
        self.name = name
        fspath = os.path.join(currentdir, name)
        if os.path.isdir(fspath):
            self.type = "dir"
            self.key = "0" + name
        else:
            self.type = "name"
            self.key = "1" + name


def get_path_list(path):
    pathes = path.split("/")
    last = None
    pathlist = []
    for vpath in pathes:
        if vpath == "":
            continue
        if last is not None:
            vpath = last + "/" + vpath
        pathlist.append(vpath)
        last = vpath
    return pathlist


def handle_layout(kw):
    kw.show_aside = False
    embed = xutils.get_argument_bool("embed")
    kw.embed = embed
    if embed:
        kw.show_menu = False
        kw.show_search = False
        kw.show_path = True
        kw.show_nav = False


class PreviewHandler:

    def GET(self, path=""):
        if path == "":
            path = xutils.get_argument_str("path")
        else:
            path = xutils.unquote(path)

        basename = os.path.basename(path)
        op = xutils.get_argument("op")
        path = xconfig.resolve_config_path(path)
        path = xutils.get_real_path(path)
        kw = Storage()

        if os.path.isfile(path):
            check_resource(path)
            type = "file"
            content = xutils.readfile(path)
            _, ext = os.path.splitext(path)
            if ext == ".csv" and not content.startswith("```csv"):
                content = "```csv\n" + content + "\n```"
        else:
            # file not exists or not readable
            content = "File \"%s\" does not exists" % path
            type = "file"

        handle_layout(kw)
        return render("code/preview.html",
                      html_title=basename,
                      os=os,
                      path=path,
                      content=content,
                      type=type,
                      has_readme=False, **kw)

    def POST(self, name):
        return self.edit_POST(name)

    def edit_POST(self, path):
        path = xutils.unquote(path)
        params = web.input(content=None)
        content = params.get("content")
        new_name = params.get("new_name")
        old_name = params.get("old_name")
        if new_name != old_name:
            print("rename %s to %s" % (old_name, new_name))
            dirname = os.path.dirname(path)
            realdirname = os.path.join(WIKI_PATH, dirname)
            oldpath = os.path.join(realdirname, old_name)
            newpath = os.path.join(realdirname, new_name)
            os.rename(oldpath, newpath)
            realpath = newpath
            path = dirname + "/" + new_name
        else:
            realpath = os.path.join(WIKI_PATH, path)
        print(path, content)
        xutils.backupfile(realpath, rename=True)
        xutils.savefile(realpath, content)
        raise web.seeother("/wiki/" + xutils.quote(path))

    def edit_GET(self, name):
        name = xutils.unquote(name)
        origin_name = name
        path = os.path.join(WIKI_PATH, name)

        if name == "":
            name = "/"
        else:
            name = "/" + name
        if os.path.isdir(path):
            type = "dir"
            content = None
            children = []
            parent = name
            for child in os.listdir(path):
                if child.startswith("_"):
                    continue
                children.append(FileItem(parent, child, path))
            children.sort(key=lambda item: item.key)
        if not os.path.exists(path):
            type = "file"
            content = ""
            children = None
        else:
            type = "file"
            content = xutils.readfile(path)
            children = None

        parent = os.path.dirname(name)
        parentname = os.path.basename(parent)
        if parentname == "":
            parentname = "/"

        return render("code/wiki_edit.html",
                      show_aside=False,
                      os=os,
                      parent=parent,
                      parentname=parentname,
                      wikilist=get_path_list(name),
                      name=origin_name,
                      basename=os.path.basename(name),
                      children=children,
                      content=content,
                      type=type)


class ReadOnlyHandler:

    def GET(self, path=None):
        realpath = os.path.join(xconfig.TMP_DIR, path)
        content = xutils.readfile(realpath)
        return xtemplate.render("code/preview.html",
                                os=os, content=content, type="file")


xurls = (
    r"/code/wiki/(.*)", PreviewHandler,
    r"/code/wiki", PreviewHandler,
    r"/code/preview", PreviewHandler
)
