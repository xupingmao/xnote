# encoding=utf-8
# Created by xupingmao on 2017/04/20
import os

import web
import xauth
import xutils

from handlers.base import get_argument

class handler:

    @xauth.login_required("admin")
    def POST(self):
        type = get_argument("type")
        code = get_argument("code")
        stream = os.popen(code)
        # return xutils.json_str(status=status, result=result)

        buf_size = 1024
        buf = stream.read(buf_size)
        while buf:
            yield buf
            buf = stream.read(buf_size)
