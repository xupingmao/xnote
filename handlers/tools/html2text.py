# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/04/30
# 

"""Description here"""

import web
from html2text import HTML2Text, main

from handlers.base import BaseHandler
import xutils

class handler(BaseHandler):
    def default_request(self):
        try:
            url = xutils.get_argument("url")
            if url is None or url == "":
                raise Exception("url为空")
            h = HTML2Text(baseurl = url)
            data = xutils.http_get(url)
            text = h.handle(data)
            # return dict(text=text)
        except Exception as e:
            text = "错误:" + str(e)
        web.header("Content-Type", "text/plain; charset=utf-8")
        return text


if __name__ == "__main__":
    main()
