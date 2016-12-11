from web import xtemplate

class handler:

    def GET(self):
        return xtemplate.render("tools/color.html")

name = "颜色"
description="常用颜色"