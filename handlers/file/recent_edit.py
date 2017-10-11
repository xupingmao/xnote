#coding:utf-8
import math

from handlers.base import *
from .dao import *

import xconfig
import xauth
import xutils

# 兼容旧代码
config = xconfig

def execute(sql):
    return xutils.db_execute(config.DB_PATH, sql)

# 待优化
def get_recent_modified(days, page=1, pagesize=config.PAGE_SIZE):
    user_name = xauth.get_current_name()
    # if user_name == "admin":
    #     # sql = "select * from file where smtime > '%s' AND is_deleted != 1 order by smtime desc"\
    #     # % dateutil.before(days=int(days), format=True)
    #     sql = "select * from file where is_deleted != 1"
    # else:
    #     sql = "select * from file where is_deleted != 1 AND groups = '%s'" % user_name

    sql = "select * from file where is_deleted != 1 AND creator = '%s'" % user_name

    sql += " ORDER BY smtime DESC"
    sql += " LIMIT %s, %s" % ((page-1) * pagesize, pagesize)
    list = execute(sql)
        
    return [FileDO.fromDict(item) for item in list]

def count_files():
    if xauth.get_current_user() == None:
        return 0
    user_name = xauth.get_current_user().get("name")
    # if user_name == "admin":
    #     count = execute("SELECT COUNT(*) as count FROM file WHERE is_deleted = 0 ")[0].get("count")
    # else:
    #     count = execute("SELECT COUNT(*) as count FROM file WHERE is_deleted = 0 AND groups='%s'" % user_name)[0].get("count")
    count = execute("SELECT COUNT(*) as count FROM file WHERE is_deleted = 0 AND groups='%s'" % user_name)[0].get("count")
    if count == 0:
        return 1
    return count

class handler(BaseHandler):
    """show recent modified files"""

    @xauth.login_required()
    def execute(self):
        s_days = self.get_argument("days", 30)
        page = int(self.get_argument("page", 1))
        page = max(1, page)
        days = int(s_days)
        files = get_recent_modified(days, page)
        count = count_files()
        self.render("file/view.html", 
            pathlist = [Storage(name="最近编辑", url="/file/recent_edit")],
            file_type = "group",
            files = files[:20], 
            page = page, 
            page_max = math.ceil(count/config.PAGE_SIZE), 
            page_url="/file/recent_edit?page=")

    def json_request(self):
        s_days = self.get_argument("days", 7)
        days = int(s_days)
        files = get_recent_modified(days)
        return files

