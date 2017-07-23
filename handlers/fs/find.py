# encoding=utf-8

import os
import glob
import xutils
import xtemplate

def limited_glob(pattern, limit = 256):
    dirname = os.path.dirname(pattern)
    pattern = os.path.basename(pattern)
    return _limited_glob(dirname, pattern, [], limit)

def _limited_glob(dirname, pattern, result, limit):
    print("%60s%20s" % (dirname, pattern))
    result += glob.glob(os.path.join(dirname, pattern), recursive=False)
    for name in os.listdir(dirname):
        path = os.path.join(dirname, name)
        if os.path.isdir(path):
            _limited_glob(path, pattern, result, limit)
        if len(result) > limit:
            return result
    return result

class handler:

    def GET(self):
        return self.POST()

    def POST(self):
        path = xutils.get_argument("path")
        find_key = xutils.get_argument("find_key")
        path_name = os.path.join(path, find_key)
        plist = limited_glob(path_name)
        # print(path, find_key)
        return xtemplate.render("fs/fs.html", 
            path = path,
            find_key=find_key, 
            fspathlist = xutils.splitpath(path),
            filelist = [xutils.FileItem(p, path) for p in plist])
