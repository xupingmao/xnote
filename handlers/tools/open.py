from BaseHandler import *

class OpenHandler(BaseHandler):
    
    def default_request(self):
        path = self.get_argument("path")
        if os.path.isdir(path):
            if osutil.iswindows():
                cmd = "explorer %s" % path
            elif osutil.ismac():
                cmd = "find %s" % path
        else:
            cmd = path
        os.popen(cmd)
        return "<html><script>window.close()</script></html>"

handler = OpenHandler