from web.xtemplate import render
import os
from util import fsutil

def loadfile(name):
    path = os.path.join("static/wiki/", name)
    return fsutil.readfile(path)

class WikiHandler:

    def GET(self, name):
        return render("wiki.html", filename = name, 
            content = loadfile(name))