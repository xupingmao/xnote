# encoding=utf-8

import os
import web
import xutils
from xutils import quote


class UploadHandler:

    def POST(self):
        args = web.input(file = {}, dirname = None)
        x = args
        dirname = args.dirname
        if 'file' in x:
            if x.file.filename == "":
                raise web.seeother("//fs/%s" % quote(dirname))
            xutils.makedirs(dirname)
            filename = xutils.quote(x.file.filename)
            filepath = os.path.join(dirname, filename)
            with open(filepath, "wb") as fout:
                # fout.write(x.file.file.read())
                for chunk in x.file.file:
                    fout.write(chunk)
        raise web.seeother("/fs/%s" % quote(dirname))

class RangeUploadHandler:

    def POST(self):
        pass

xurls = ("/fs_upload", UploadHandler, "/fs/upload/range", RangeUploadHandler)
