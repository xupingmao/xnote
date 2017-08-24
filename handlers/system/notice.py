# encoding=utf-8
# Created by xupingmao on 2017/08/24
import xtemplate
import xutils

class handler:
    def GET(self):
        content = xutils.get_argument("content")
        return xtemplate.render("system/notice.html", content=content)