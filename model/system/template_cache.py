from BaseHandler import *

class handler(BaseHandler):

    def default_request(self):
        name = self.get_argument("name", "")
        if name == "":
            self.render("system/template_cache.html")
        else:
            try:
                code = get_template_code(name)
            except:
                code = ""
            self.render("system/template_cache.html", code=code)

searchkey = "模板代码|inspect_template"