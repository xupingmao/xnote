from BaseHandler import *


class handler(BaseHandler):

    def execute(self):
        raise web.seeother("/fs/D:/")

name = "文件系统"
description = "下载和上传文件"