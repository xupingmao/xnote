# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/18
# 

"""Description here"""
import re

import xauth
import xutils
from . import dao

class handler:

    @xauth.login_required()
    def GET(self):
        # days = xutils.get_argument("days", 30, type=int)
        offset = xutils.get_argument("offset", 0, type=int)
        limit  = xutils.get_argument("limit", 20, type=int)
        db = dao.get_file_db()
        # last_month = xutils.days_before(days, format=True)
        user_name  = xauth.get_current_user()["name"]
        rows = db.query("SELECT * FROM file WHERE creator = $creator AND is_deleted=0"
            + " ORDER BY sctime DESC LIMIT $offset, $limit", 
            dict(creator=user_name, offset=offset, limit=limit))
        result = dict()
        for row in rows:
            date = re.match(r"\d+\-\d+", row.sctime).group(0)
            row.url = "/file/view?id={}".format(row.id);
            # 优化数据大小
            row.content = ""
            if date not in result:
                result[date] = []
            result[date].append(row)

        return xutils.json_str(**result)

class DateTimeline:
    @xauth.login_required()
    def GET(self):
        year  = xutils.get_argument("year")
        month = xutils.get_argument("month")
        if len(month) == 1:
            month = "0" + month
        db = dao.get_file_db()
        user_name  = xauth.get_current_user()["name"]
        rows = db.query("SELECT * FROM file WHERE creator = $creator AND sctime LIKE $ctime AND is_deleted=0"
            + " ORDER BY sctime DESC", 
            dict(creator=user_name, ctime="%s-%s%%" % (year, month)))
        result = dict()
        for row in rows:
            date = re.match(r"\d+\-\d+", row.sctime).group(0)
            row.url = "/file/view?id={}".format(row.id);
            # 优化数据大小
            row.content = ""
            if date not in result:
                result[date] = []
            result[date].append(row)

        return xutils.json_str(**result)

xurls = (
    r"/file/timeline", handler,
    r"/file/timeline/month", DateTimeline
)

