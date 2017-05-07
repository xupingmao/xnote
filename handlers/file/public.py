# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/07
# 

"""Description here"""

import xtemplate
import xauth
import handlers.base as base
from xutils import Storage
from . import dao

def get_recent_modified(limit, page=0):
    db = dao.FileDB()
    count = db.execute("SELECT COUNT(*) AS _cnt FROM file WHERE is_deleted != 1 AND groups = '*'")[0].get("_cnt")
    sql = "SELECT * FROM file WHERE is_deleted != 1 AND groups = '*'"
    sql += " ORDER BY smtime DESC LIMIT %s, %s" % (page * limit, limit)
    all = db.execute(sql)
    files = [dao.FileDO.fromDict(item) for item in all]
    return Storage(count = count, files = files)

class handler:

    @xauth.login_required()
    def GET(self):
        page = base.get_argument("page", 1, type=int)
        recent = get_recent_modified(10, page-1)
        return xtemplate.render("file-list.html", 
            count=recent.count, 
            files=recent.files, 
            page=page,
            page_url="/file/public?page=")

