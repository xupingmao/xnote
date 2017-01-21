from BaseHandler import *


class handler:

    def POST(self):
        args = web.input(name="", password="", target=None)
        name = args["name"]
        pswd = args["password"]
        target = args["target"]

        print("USER[%s] PSWD[%s]" % (name, pswd))
        # FIXME prevent hack
        if name == "admin" and pswd == "123456":
            web.setcookie("xuser", "admin", expires=10 * 24 * 3600)
            if target is None:
                raise web.seeother("/")
            raise web.seeother(target)
        return render_template("login.html", name=name, password=pswd, _has_login=True)


    def GET(self):
        args = web.input(name="", password="")
        name = args["name"]
        pswd = args["password"]
        return render_template("login.html", name = name, password=pswd, _has_login=True)