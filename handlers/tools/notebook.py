# encoding=utf-8

import web
import xutils
import xtemplate


class handler:

    def GET(self):
        return xtemplate.render("tools/notebook.html")
        
    def POST(self):
        args = web.input()
        option = args.op
        if option == "add":
            content = args.content

        return xutils.json_str(success=True)
