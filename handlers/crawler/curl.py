from handlers.base import *
from urllib.request import urlopen

class CurlHandler(BaseHandler):

    def default_request(self):
        url = self.get_argument("url", "")
        if url == "":
            # get from header
            return ""
        else:
            url = netutil.get_http_home(url)
        stream = urlopen(url)
        return stream.read()


handler = CurlHandler