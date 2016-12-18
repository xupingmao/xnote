from BaseHandler import *

class handler(BaseHandler):

    def execute(self):
        attachment = ("Content-Diposition", "attachment; filename=\"%s\"" % "data.db")
        web.ctx.headers.append(attachment)
        return open("data.db", "rb").read()