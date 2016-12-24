from web import xtemplate
import xutils

class handler:
    __xurl__ = "/tools/(.*)"
    
    def GET(self, name):
        name = xutils.unquote(name)
        return xtemplate.render("tools/" + name)