from BaseHandler import *
from urllib.request import urlopen

searchable = False

class handler(BaseHandler):

    def default_request(self):
        path = self.get_argument("path", "")
        url  = self.get_argument("url", "")
        if not url.startswith("http://"):
            url = "http://" + url
        content = urlopen(url + "/sync?path=" + path).read()
        # \n will be replaced to \r\n ?
        # content = content.replace("\r\n", "\n")
        # backup local file
        fsutil.writebytes(path, content)
        return "success"