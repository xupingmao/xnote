from web import xtemplate


class handler:
    __url__ = "/tools/(.*)"
    
    def GET(self, name):
        return xtemplate.render("tools/" + name)