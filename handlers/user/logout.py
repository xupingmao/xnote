# encoding=utf-8
import xtemplate
import web

class handler:

    def GET(self):
        web.setcookie("xuser", "", expires=-1)
        raise web.seeother("/")

xurls = (
    r"/logout", handler
)