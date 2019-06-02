# encoding=utf-8
# Created by xupingmao on 2017/06/22
import web
import xauth

class handler:

    @xauth.login_required("admin")
    def GET(self):
        headers = dict()
        for key in web.ctx.env:
            headers[key] = str(web.ctx.env.get(key))
        return dict(code="success", data=headers)

    def POST(self):
        return self.GET()

        