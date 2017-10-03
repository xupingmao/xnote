# encoding=utf-8

import os
import glob
import xutils
import xtemplate

from fnmatch import fnmatch

def limited_glob(pattern, limit = 256):
    dirname = os.path.dirname(pattern)
    pattern = os.path.basename(pattern)
    return _limited_glob(dirname, pattern, [], limit)

def _limited_glob(dirname, pattern, result, limit):
    # print("%60s%20s" % (dirname, pattern))
    # result += glob.glob(os.path.join(dirname, pattern), recursive=False)
    path = os.path.join(dirname, pattern)
    result += glob.glob(path)

    # 处理urlencode的文件系统
    quoted_path = xutils.quote_unicode(path)
    if quoted_path != path:
        result += glob.glob(quoted_path)
    
    for name in os.listdir(dirname):
        path = os.path.join(dirname, name)
        if os.path.isdir(path):
            _limited_glob(path, pattern, result, limit)
        if len(result) > limit:
            return result
    return result

def find_with_fnmatch0(path, key, limit=200):
    result_dirs = []
    result_files = []
    key = key.lower()
    count = 0
    for root, dirs, files in os.walk(path):
        for f in dirs:
            abspath = os.path.join(root, f)
            if fnmatch(abspath.lower(), key):
                result_dirs.append(abspath)
                count+=1
                if count >= limit:
                    break
        for f in files:
            abspath = os.path.join(root, f)
            if fnmatch(abspath.lower(), key):
                result_files.append(abspath)
                count+=1
                if count >= limit:
                    break
    return result_dirs + result_files

def find_with_fnmatch(path, key):
    result = []
    quoted_key = xutils.quote_unicode(key)
    if key != quoted_key:
        result = find_with_fnmatch0(path, quoted_key)
    return result + find_with_fnmatch0(path, key)

class handler:

    def GET(self):
        return self.POST()

    def POST(self):
        path = xutils.get_argument("path")
        find_key = xutils.get_argument("find_key")
        find_type = xutils.get_argument("type")
        find_key = "*" + find_key + "*"
        path_name = os.path.join(path, find_key)
        if find_key == "":
            plist = []
        elif find_type == "glob":
            plist = limited_glob(path_name)
        else:
            plist = find_with_fnmatch(path, find_key)
        # plist = glob.glob(path_name)
        # plist += glob.glob(os.path.join(path, quoted_key))
        # print(path, find_key)
        return xtemplate.render("fs/fs.html", 
            fspathlist = xutils.splitpath(path),
            filelist = [xutils.FileItem(p, path) for p in plist])
