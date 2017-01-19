import xtemplate
import web

class handler:

    def GET(self):
        web.setcookie("xuser", None)
        return xtemplate.render("base.html")