# encoding=utf-8
import hashlib
import xauth

class handler:

    def POST(self):
        args = web.input(name="", password="", target=None)
        name = args["username"]
        pswd = args["password"]
        target = args["target"]

        print("USER[%s] PSWD[%s]" % (name, pswd))

        users = xauth.get_users()

        error = ""
        if name in users:
            user = users[name]
            if pswd == user["password"]:
                web.setcookie("xuser", name, expires= 24 * 3600)
                pswd_md5 = hashlib.md5()
                pswd_md5.update(pswd.encode("utf-8"))
                web.setcookie("xpass", pswd_md5.hexdigest(), expires=24*3600)
                if target is None:
                    raise web.seeother("/")
                raise web.seeother(target)
            else:
                error = "password error"
        else:
            error = "user not exists"
        return render_template("login.html", 
            username=name, 
            password=pswd,
            _has_login=True,
            error = error)


    def GET(self):
        args = web.input(username="", password="")
        name = args["username"]
        pswd = args["password"]
        return render_template("login.html", 
            username = name, 
            password=pswd, 
            _has_login=True,
            error = "")


