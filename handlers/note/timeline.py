# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/18
# @modified 2018/09/11 01:07:53

"""Description here"""
import re
import xauth
import xutils
import xtables

class handler:

    @xauth.login_required()
    def GET(self):
        # days = xutils.get_argument("days", 30, type=int)
        offset = xutils.get_argument("offset", 0, type=int)
        limit  = xutils.get_argument("limit", 20, type=int)
        db = xtables.get_file_table()
        # last_month = xutils.days_before(days, format=True)
        user_name  = xauth.get_current_user()["name"]
        rows = db.query("SELECT id, type, name, creator, ctime, mtime, size FROM file WHERE creator = $creator AND is_deleted=0"
            + " ORDER BY ctime DESC LIMIT $offset, $limit", 
            dict(creator=user_name, offset=offset, limit=limit))
        result = dict()
        for row in rows:
            date = re.match(r"\d+\-\d+", row.ctime).group(0)
            row.url = "/note/view?id={}".format(row.id);
            # 优化数据大小
            row.content = ""
            if date not in result:
                result[date] = []
            result[date].append(row)
        return result

class DateTimeline:
    @xauth.login_required()
    def GET(self):
        year  = xutils.get_argument("year")
        month = xutils.get_argument("month")
        if len(month) == 1:
            month = "0" + month
        db = xtables.get_file_table()
        user_name  = xauth.get_current_user()["name"]
        rows = db.query("SELECT id, type, name, creator, ctime, mtime, size FROM file WHERE creator = $creator AND ctime LIKE $ctime AND is_deleted=0"
            + " ORDER BY ctime DESC", 
            dict(creator=user_name, ctime="%s-%s%%" % (year, month)))
        result = dict()
        for row in rows:
            date = re.match(r"\d+\-\d+", row.ctime).group(0)
            row.url = "/note/view?id={}".format(row.id);
            # 优化数据大小
            row.content = ""
            if date not in result:
                result[date] = []
            result[date].append(row)
        return result

xurls = (
    r"/file/timeline", handler,
    r"/note/timeline", handler,
    r"/file/timeline/month", DateTimeline,
    r"/note/timeline/month", DateTimeline
)

