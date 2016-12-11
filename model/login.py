from BaseHandler import *


class handler:

    def POST(self):
        args = web.input(name="", password="", target=None)
        name = args["name"]
        pswd = args["password"]
        target = args["target"]

        print("USER[%s] PSWD[%s]" % (name, pswd))
        if name == "xpm" and pswd == "xlg":
            web.setcookie("xuser", "admin", expires=10 * 24 * 3600)
            web.seeother(target)
            return

        return render_template("login.html", name=name, password=pswd)


    def GET(self):
        args = web.input(name=None, password=None)
        name = args["name"]
        pswd = args["password"]
        return render_template("login.html", name = name, password=pswd)