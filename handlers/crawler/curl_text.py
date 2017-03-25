from handlers.base import *
from urllib.request import urlopen
import re

class handler(BaseHandler):

    def default_request(self):
        url = self.get_argument("url", "")
        if url != "":
            content = urlopen(url).read()
            self.render("curl-text.html", content = content)
        else:
            self.render("curl-text.html")