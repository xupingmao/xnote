from xtemplate import render, reload
import web
import autoreload

class handler:
    def GET(self):
        autoreload.reload()
        raise web.seeother("/system/sys")