#coding:utf-8
import math
import xconfig
import xauth
import xutils
import xtables
import xtemplate
from .dao import *
from xutils import Storage

# 兼容旧代码
config = xconfig

# 待优化
def get_recent_modified(days, page=1, pagesize=config.PAGE_SIZE):
    user_name = xauth.get_current_name()
    sql = "SELECT * FROM file WHERE is_deleted = 0 AND (creator = $creator OR is_public = 1)"
    sql += " ORDER BY mtime DESC"
    sql += " LIMIT %s, %s" % ((page-1) * pagesize, pagesize)
    list = xtables.get_file_table().query(sql, vars=dict(creator=user_name))
    return [FileDO.fromDict(item) for item in list]

def count_files():
    if xauth.get_current_user() == None:
        return 0
    user_name = xauth.get_current_name()
    db = xtables.get_file_table()
    count = db.count("is_deleted = 0 AND (creator = $creator OR is_public = 1)", vars = dict(creator=user_name))
    return count

class handler:
    """show recent modified files"""

    @xauth.login_required()
    def GET(self):
        days = xutils.get_argument("days", 30, type=int)
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        files = get_recent_modified(days, page)
        count = count_files()
        return xtemplate.render("file/view.html", 
            pathlist = [Storage(name="最近编辑", url="/file/recent_edit")],
            file_type = "group",
            files = files[:20], 
            page = page, 
            page_max = math.ceil(count/config.PAGE_SIZE), 
            page_url="/file/recent_edit?page=")


