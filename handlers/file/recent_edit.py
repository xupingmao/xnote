#coding:utf-8
from handlers.base import *
from FileDB import *

import config
import xauth
import xutils

def execute(sql):
    return xutils.db_execute("db/data.db", sql)

# 待优化
def get_recent_modified(days, page=1, pagesize=config.PAGE_SIZE):
    user = xauth.get_current_user()
    if user is None:
        return []
    user_name = user["name"]
    if user_name == "admin":
        # sql = "select * from file where smtime > '%s' AND is_deleted != 1 order by smtime desc"\
        # % dateutil.before(days=int(days), format=True)
        sql = "select * from file where is_deleted != 1 order by smtime desc"
    else:
        sql = "select * from file where smtime > '%s' AND is_deleted != 1 AND (groups='%s' OR groups='*') order by smtime desc"\
        % (dateutil.before(days=int(days), format=True), user_name)
    sql += " LIMIT %s, %s" % ((page-1) * pagesize, pagesize)
    list = execute(sql)
        
    return [FileDO.fromDict(item) for item in list]

def get_pages():
    return execute("SELECT COUNT(*) as count FROM file WHERE is_deleted = 0")[0].get("count")

class handler(BaseHandler):
    """show recent modified files"""
    def execute(self):
        s_days = self.get_argument("days", 30)
        page = int(self.get_argument("page", 1))
        page = max(1, page)
        days = int(s_days)
        files = get_recent_modified(days, page)
        pages = get_pages()
        self.render("file-list.html", files = files[:20], key = "", 
            page = page, pages = pages, page_url="/file/recent_edit?page=")

    def json_request(self):
        s_days = self.get_argument("days", 7)
        days = int(s_days)
        files = get_recent_modified(days)
        return files

