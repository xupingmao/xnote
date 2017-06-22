# encoding=utf-8
import web

class handler:

    def GET(self):
        headers = dict()
        for key in web.ctx.env:
            headers[key] = str(web.ctx.env.get(key))
        return dict(code="success", data=headers)

    def POST(self):
        return self.GET()

        