from BaseHandler import *
from web.tornado.escape import xhtml_escape

import xutils

class ViewSourceHandler(BaseHandler):

    def default_request(self):
        path = self.get_argument("path", "")
        key  = self.get_argument("key", "")
        if path == "":
            self.render("code/view-source.html", error = "path is empty")
        else:
            try:
                content = xutils.readfile(path)
                if key != "":
                    content = xutils.html_escape(content)
                    key     = xhtml_escape(key)
                    content = textutil.replace(content, key, htmlutil.span("?", "search-key"), ignore_case=True, use_template=True)
                self.render("code/view-source.html", content = content, lines = content.count("\n") + 1)
            except Exception as e:
                self.render("code/view-source.html", error = e, lines = 0)

handler = ViewSourceHandler