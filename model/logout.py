import xtemplate
import web

class handler:

    def GET(self):
        web.setcookie("xuser", None)
        raise web.seeother("/")