# encoding=utf-8
import os
import xutils
import xauth

class handler:
    
    @xauth.login_required("admin")
    def GET(self):
        path = xutils.get_argument("path")
        if os.path.isdir(path):
            path = '"%s"' % path
            if xutils.is_windows():
                path = path.replace("/", "\\")
                cmd = "explorer %s" % path
            elif xutils.is_mac():
                cmd = "find %s" % path
        else:
            cmd = path
        print(cmd)
        os.popen(cmd)
        return "<html><script>window.close()</script></html>"

    def POST(self):
        return self.GET()
