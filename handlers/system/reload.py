# encoding=utf-8
from xtemplate import render, reload
import web
import autoreload
import xauth

class handler:
    @xauth.login_required("admin")
    def GET(self):
        autoreload.reload()
        raise web.seeother("/")