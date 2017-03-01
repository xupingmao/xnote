import web
import xtemplate

class handler:

    def GET(self):
        name = web.input(name="").name
        if name == "":
            return xtemplate.render("system/template_cache.html", name=name)
        else:
            if not name.endswith(".html"):
                name += ".html"
            try:
                code = xtemplate.get_code(name)
            except:
                code = ""
            return xtemplate.render("system/template_cache.html", code=code, name=name)

