from BaseHandler import *
import xutils


class handler(BaseHandler):

    __url__ = r"/fs-"

    def execute(self):
        if xutils.is_windows():
            raise web.seeother("/fs-D:/")
        else:
            raise web.seeother("/fs-/")

name = "文件系统"
description = "下载和上传文件"