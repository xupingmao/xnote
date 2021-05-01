# encoding=utf-8
import xtemplate
import web
import xauth

class LogoutHandler:

    def GET(self):
        xauth.logout_current_user()
        web.setcookie("sid", "", expires=-1)
        raise web.seeother("/")

xurls = (
    r"/logout", LogoutHandler
)