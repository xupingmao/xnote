# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/07
# 

"""Description here"""

import xtemplate

from xutils import Storage
from . import dao

def get_recent_modified(count):
    db = dao.FileDB()
    count = db.execute("SELECT COUNT(*) AS _cnt FROM file WHERE is_deleted != 1 AND groups = '*'")[0].get("_cnt")
    all = db.execute("SELECT * FROM file WHERE is_deleted != 1 AND groups = '*' ORDER BY smtime DESC LIMIT %s" % count)
    files = [dao.FileDO.fromDict(item) for item in all]
    return Storage(count = count, files = files)

class handler:

    def GET(self):
        recent = get_recent_modified(10)
        return xtemplate.render("file-list.html", 
            count=recent.count, 
            files=recent.files, 
            page=1,
            page_url="/file/public?page=")

