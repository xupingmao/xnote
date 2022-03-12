
import xutils
import xtemplate

class handler:    
    def GET(self):
        return "success"


class ExampleHandler:

    def GET(self):
        name = xutils.get_argument("name", "")
        if name == "":
            return xtemplate.render("test/page/example_index.html")
        else:
            return xtemplate.render("test/page/example_%s.html" % name)


xurls = (
    r"/test", handler,
    r"/test/example", ExampleHandler,
)
