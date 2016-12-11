from web.xtemplate import render
import os
import xutils

WIKI_PATH = "static/wiki/"

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
    __url__ = r"/wiki/(.*)"
    
    def GET(self, name):
        name = xutils.unquote(name)
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
            
        return render("wiki.html", 
            os = os,
            parent = parent,
            parentname = parentname,
            name = os.path.basename(name), 
            children = children,
            content = content,
            type = type)