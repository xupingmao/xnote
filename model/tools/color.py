from BaseHandler import *

class handler(BaseHandler):

    def default_request(self):
        self.render()

name = "颜色"
description="常用颜色"