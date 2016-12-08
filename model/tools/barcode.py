from BaseHandler import *


class handler(BaseHandler):

    def default_request(self):
        return self.render()

name = "二维码生成器"