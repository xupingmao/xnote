# encoding=utf-8

import os
import web
import xutils
from util import fsutil
from xutils import quote


class handler:

    def POST(self):
        args = web.input(file = {}, dirname = None)
        x = args
        dirname = args.dirname
        if 'file' in x:
            if x.file.filename == "":
                raise web.seeother("//fs/%s" % quote(dirname))
            fsutil.check_create_dirs(dirname)
            filename = xutils.quote(x.file.filename)
            filepath = os.path.join(dirname, filename)
            with open(filepath, "wb") as fout:
                # fout.write(x.file.file.read())
                for chunk in x.file.file:
                    fout.write(chunk)
        raise web.seeother("//fs/%s" % quote(dirname))

xurls = ("/fs_upload", handler)
