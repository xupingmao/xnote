# encoding=utf-8

import xtemplate
import xauth
from . import dao

def to_date(s):
    if s is None:
        return ''
    return s[:s.find(' ')]

class handler:

    @xauth.login_required("admin")
    def GET(self):
        recent_created = dao.get_recent_created(7)
        recent_modified = dao.get_recent_modified(7)
        return xtemplate.render("file/summary.html", 
            recent_created = recent_created,
            recent_modified = recent_modified,
            to_date=to_date)

