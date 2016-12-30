from web.xtemplate import render
import os
import xutils
import web

WIKI_PATH = "static/wiki/"

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
    __url__ = r"/wiki/?(.*)"
    
    def GET(self, name):
        name = xutils.unquote(name)
        origin_name = name
        path = os.path.join(WIKI_PATH, name)
        
        if name == "":
            name = "/"
        else:
            name = "/" + name

        has_readme = False

        if os.path.isdir(path):
            type = "dir"
            content = None
            children = []
            parent = name
            for child in os.listdir(path):
                _, ext = os.path.splitext(child)
                if child.startswith("_"):
                    continue
                if ext in HIDE_EXT_LIST:
                    continue
                # if child.lower() in ["index.md", "readme.md"]:
                #     has_readme = True
                #     content = xutils.readfile(os.path.join(path, child))
                #     continue
                children.append(FileItem(parent, child, path))
            children.sort(key = lambda item: item.key)
        elif os.path.isfile(path):
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
            content = "File \"%s\" not exists" % origin_name
            type = "file"
        
        parent = os.path.dirname(name)
        parentname = os.path.basename(parent)
        if parentname=="":
            parentname="/"
            
        return render("wiki/wiki.html", 
            os = os,
            parent = parent,
            parentname = parentname,
            wikilist = get_path_list(name),
            name = origin_name,
            children = children,
            content = content,
            type = type,
            has_readme = has_readme)