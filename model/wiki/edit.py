from web.xtemplate import render
import os
import xutils
import web

WIKI_PATH = "static/wiki/"

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
        

        
       
class handler:
    __url__ = r"/wiki/edit/(.*)"
    
    
    def POST(self, path):
        path = xutils.unquote(path)
        content = web.input(content=None).get("content")
        print(path, content)
        realpath = os.path.join(WIKI_PATH, path)
        xutils.backupfile(realpath)
        xutils.savefile(realpath, content)
        raise web.seeother("/wiki/edit/" + xutils.quote(path))
    
    def GET(self, name):
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
        else:
            type = "file"
            content = xutils.readfile(path)
            children = None
        
        parent = os.path.dirname(name)
        parentname = os.path.basename(parent)
        if parentname=="":
            parentname="/"
            
        return render("wiki/edit.html", 
            os = os,
            parent = parent,
            parentname = parentname,
            wikilist = get_path_list(name),
            name = origin_name,
            children = children,
            content = content,
            type = type)