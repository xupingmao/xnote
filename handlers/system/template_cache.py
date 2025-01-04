import web
import xutils
from xutils import Storage
from xnote.core import xtemplate
from xnote.core import xauth

class handler:

    @xauth.login_required("admin")
    def GET(self):
        name = xutils.get_argument_str("name")
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
            lines = code.split("\n")
            kw = Storage()
            kw.code = code
            kw.lines = lines
            kw.templates = templates
            return xtemplate.render("system/page/template_cache.html", **kw)

