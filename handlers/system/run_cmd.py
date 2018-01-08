# encoding=utf-8
# Created by xupingmao on 2017/04/20
import os
import web
import xauth
import xutils

class handler:

    @xauth.login_required("admin")
    def POST(self):
        type = xutils.get_argument("type")
        code = xutils.get_argument("code")
        stream = os.popen(code)
        buf_size = 1024
        buf = stream.read(buf_size)
        while buf:
            yield buf
            buf = stream.read(buf_size)
