from web.utils import Storage
from BaseHandler import *
import posixpath
import functools

class DirectoryFile(Storage):
    def __init__(self, type, name, root, fullpath = None):
        Storage.__init__(self)
        self.type = type
        self.name = name
        if root[-1] == "/":
            self.webpath = root + name
        else:
            self.webpath = root + "/" + name

        if type != "dir" and fullpath:
            self.size = fsutil.get_file_size(fullpath)
        
    def __cmp__(self, other):
        if self['type'] == "dir" and other['type'] == "file":
            return -1
        if self['type'] == "file" and other['type'] == "dir":
            return 1
        if self['name'] > other['name']: 
            return 1
        if self['name'] < other['name']: 
            return -1
        return 0
        
def getFiles(webpath, ext=None):
    WORKING_DIR = config.WORKING_DIR
    root = WORKING_DIR
    if webpath[0] == "/":
        dir = os.path.join(WORKING_DIR, webpath[1:])
    else:
        dir = os.path.join(WORKING_DIR, webpath)
    files = []
    if webpath != "/static":
        parent = posixpath.dirname(webpath)
        webfile = DirectoryFile("dir", "..", parent)
        webfile.webpath = parent
        files.append(webfile)
    for name in os.listdir(dir):
        fullpath = os.path.join(dir, name)
        isDir = os.path.isdir(fullpath)
        if not isDir and ext is not None and not name.endswith(ext):
            continue
        path = os.path.join(webpath, name)
        path = posixpath.normpath(path)
        if isDir:
            files.append(DirectoryFile("dir", name, webpath, fullpath))
        else:
            files.append(DirectoryFile("file", name, webpath, fullpath))
    files.sort(key=functools.cmp_to_key(DirectoryFile.__cmp__))
    return files


class handler(BaseHandler):
    def get(self):
        webpath = self.get_argument("path", "/static")

        self.render("explorer.html", files = getFiles(webpath))

    def post(self):
        return BaseHandler.get(self)

    def listFilesRequest(self):
        path = self.get_argument("path", None)
        if path is None:
            raise HTTPError(500)
        originPath = path
        if path[0] == "/":
            path = path[1:]
        abspath = os.path.join(WEBDIR, path)
        return getFiles(abspath, originPath)
