from BaseHandler import *

searchable = False

class handler(BaseHandler):

    def default_request(self):
        return "success"