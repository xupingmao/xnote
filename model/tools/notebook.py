from BaseHandler import *

class handler(BaseHandler):

    def default_request(self):
        self.render("notebook.html")