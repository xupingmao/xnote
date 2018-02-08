# encoding=utf-8
import os
import glob
import xutils
import xauth
import xtemplate

class handler:

    def GET(self):
        return self.POST()

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument("path")
        find_key = xutils.get_argument("find_key", "")
        find_type = xutils.get_argument("type")
        find_key = "*" + find_key + "*"
        path_name = os.path.join(path, find_key)
        if find_key == "":
            plist = []
        else:
            plist = xutils.search_path(path, find_key)
        return xtemplate.render("fs/fs.html", 
            token = xauth.get_current_user().token,
            fspathlist = xutils.splitpath(path),
            filelist = [xutils.FileItem(p, path) for p in plist])

xurls = (
    r"/fs_find", handler
)
