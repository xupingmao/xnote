# encoding=utf-8
import xtemplate
import xutils

from . import dao


def date2str(d):
    ct = time.gmtime(d / 1000)
    return time.strftime('%Y-%m-%d %H:%M:%S', ct)

class handler:

    __xurl__ = "/item/(.*)"

    def GET(self, name):
        name = xutils.unquote(name)
        file = dao.get_by_name(name)
        return xtemplate.render("file/markdown.html",
            file = file,
            content = file.content,
            date2str = date2str,
            download_csv = False,
            children = [])
