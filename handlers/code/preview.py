# encoding=utf-8
import os
import web
import xutils
import xauth
import xconfig
from xtemplate import render

WIKI_PATH = "./"

HIDE_EXT_LIST = [
    ".bak"
]

def check_resource(path):
    _,ext = os.path.splitext(path)
    if ext in (".png", ".jpg"):
        pathlist = path.split("/")
        pathlist = map(lambda name: xutils.quote(name), pathlist)
        uri = "/" + "/".join(pathlist)
        # print(uri)
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

class handler:
    
    def GET(self, name=""):
        name = xutils.unquote(name)
        op   = xutils.get_argument("op")
        path = xutils.get_argument("path")
        origin_name = name
        if name == "":
            name = "/"
        else:
            name = "/" + name
        path = xutils.get_real_path(path)
        has_readme = False
        if os.path.isfile(path):
            check_resource(path)
            type = "file"
            content = xutils.readfile(path)
            _, ext = os.path.splitext(path)
            if ext == ".csv" and not content.startswith("```csv"):
                content = "```csv\n" + content + "\n```"
            children = None
        else:
            # file not exists or not readable
            children = None
            content = "File \"%s\" does not exists" % origin_name
            type = "file"
        
        parent = os.path.dirname(name)
        parentname = os.path.basename(parent)
        if parentname=="":
            parentname="/"
            
        return render("code/preview.html", 
            os = os,
            path = path,
            parent = parent,
            parentname = parentname,
            wikilist = get_path_list(name),
            name = origin_name,
            children = children,
            content = content,
            type = type,
            has_readme = has_readme)

    def POST(self, name):
        return self.edit_POST(name)

    def edit_POST(self, path):
        path = xutils.unquote(path)
        params = web.input(content=None)
        content = params.get("content")
        new_name = params.get("new_name")
        old_name = params.get("old_name")
        if new_name!=old_name:
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
            children.sort(key = lambda item: item.key)
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
        if parentname=="":
            parentname="/"
            
        return render("code/wiki_edit.html", 
            os = os,
            parent = parent,
            parentname = parentname,
            wikilist = get_path_list(name),
            name = origin_name,
            basename = os.path.basename(name),
            children = children,
            content = content,
            type = type)

# Deprecated
class ReadOnlyHandler:

    def GET(self, path=None):
        realpath = os.path.join(config.TMP_DIR, path)
        content  = xutils.readfile(realpath)
        return xtemplate.render("code/preview.html", 
            os = os, content = content, type="file")

class WikiPathHandler:

    def GET(self, path=""):
        template_name = "code/preview.html"
        if not os.path.exists(path):
            return render(template_name, error="file not exists")
        if not path.endswith(".md"):
            return render(template_name, error="file extension error")
        content = xutils.readfile(path)
        return render(template_name, content = content, os = os, type = "file", path = path)

xurls = (
    r"/wiki/(.*)", WikiPathHandler,
    r"/wiki", handler,
    r"/code/preview", handler
)

