#coding:utf-8
from handlers.base import *
from FileDB import *

import xauth
import xutils

# 待优化
def get_recent_modified(days):
    user = xauth.get_current_user()
    if user is None:
        return []
    user_name = user["name"]
    if user_name == "admin":
        sql = "select * from file where smtime > '%s' AND is_deleted != 1 order by smtime desc"\
        % dateutil.before(days=int(days), format=True)
    else:
        sql = "select * from file where smtime > '%s' AND is_deleted != 1 AND (groups='%s' OR groups='*') order by smtime desc"\
        % (dateutil.before(days=int(days), format=True), user_name)
    list = xutils.db_execute("db/data.db",sql)
        
    return [FileDO.fromDict(item) for item in list]


class handler(BaseHandler):
    """show recent modified files"""
    def default_request(self):
        s_days = self.get_argument("days", 30)
        days = int(s_days)
        files = get_recent_modified(days)
        self.render("file-list.html", files = files[:20], key = "")

    def json_request(self):
        s_days = self.get_argument("days", 7)
        days = int(s_days)
        files = get_recent_modified(days)
        return files

