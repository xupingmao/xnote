# encoding=utf-8
import os
import re
import xauth
import xutils

class handler:

    @xauth.login_required("admin")
    def GET(self):
        path    = xutils.get_argument("path")
        length  = xutils.get_argument("length", 200, type=int)
        read    = xutils.get_argument("read", "false")
        forward = xutils.get_argument("forward", "false")
        pos  = 0
        encoding = "utf-8"

        if not os.path.exists(path):
            path = xutils.quote_unicode(path)
        basename, ext = os.path.splitext(path)
        bookmarkpath = basename + ".bookmark"
        if os.path.exists(bookmarkpath):
            pos = int(xutils.readfile(bookmarkpath))

        with open(path, encoding=encoding) as fp:
            text = "dummy"
            try:
                fp.seek(pos)
                text = fp.read(length)
                if read == "true":
                    xutils.say(text)
                pos = fp.tell()
                if forward == "true":
                    xutils.savetofile(bookmarkpath, str(pos))
            except UnicodeDecodeError:
                xutils.print_exc()
                pos = 0
                xutils.savetofile(bookmarkpath, str(pos))
        return dict(code="success", data=text)

