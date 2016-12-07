from web.xtemplate import render
import os
from util import fsutil
from urllib.parse import quote, unquote

WIKI_PATH = "static/wiki/"

class WikiHandler:

    def GET(self, name):
        name = unquote(name)
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
                if parent.endswith("/"):
                    children.append(parent + child)
                else:
                    children.append(parent + "/" + child)
        else:
            type = "file"
            content = fsutil.readfile(path)
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