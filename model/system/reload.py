from web.xtemplate import render, reload
import web

class handler:
    def GET(self):
        reload()
        raise web.seeother("/system/sys")