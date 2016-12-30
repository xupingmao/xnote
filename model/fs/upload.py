import web
from util import fsutil
from xutils import quote
import os

class handler:
    
    __xurl__ = "/fs_upload"

    def POST(self):
        args = web.input(file = {}, dirname = None)
        x = args
        dirname = args.dirname
        if 'file' in x:
            if x.file.filename == "":
                raise web.seeother("/fs/%s" % quote(dirname))
            fsutil.check_create_dirs(dirname)
            filepath = os.path.join(dirname, x.file.filename)
            fout = open(filepath, "wb")
            # fout.write(x.file.file.read())
            for chunk in x.file.file:
                fout.write(chunk)
            fout.close()
        raise web.seeother("/fs/%s" % quote(dirname))