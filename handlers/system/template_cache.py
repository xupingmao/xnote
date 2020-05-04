import web
import xutils
import xtemplate

class handler:

    def GET(self):
        name = xutils.get_argument("name")
        templates = xtemplate.get_templates()
        if name == "" or name is None:
            return xtemplate.render("system/page/template_cache.html", name=name, templates=templates)
        else:
            if not name.endswith(".html"):
                name += ".html"
            try:
                code = xtemplate.get_code(name)
            except:
                code = ""
            return xtemplate.render("system/page/template_cache.html", code=code, name=name, templates=templates)

