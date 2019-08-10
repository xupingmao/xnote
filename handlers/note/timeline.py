# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/18
# @modified 2019/08/10 13:41:07

"""Description here"""
import re
import xauth
import xutils
import xtables
import xtemplate

class TimelineAjaxHandler:

    @xauth.login_required()
    def GET(self):
        offset = xutils.get_argument("offset", 0, type=int)
        limit  = xutils.get_argument("limit", 20, type=int)
        type   = xutils.get_argument("type")
        user_name  = xauth.current_name()

        if type == "mtime":
            rows = xutils.call("note.list_recent_edit", user_name, offset, limit)
        else:
            rows = xutils.call("note.list_recent_created", None, offset, limit)
        result = dict()
        for row in rows:
            if type == "mtime":
                date_time = row.mtime
            else:
                date_time = row.ctime
            date = re.match(r"\d+\-\d+", date_time).group(0)
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

class TimelineHandler:

    @xauth.login_required()
    def GET(self):
        return xtemplate.render("note/timeline.html", show_aside = False)

xurls = (
    r"/note/timeline", TimelineAjaxHandler,
    r"/note/timeline/month", DateTimeline,
    r"/note/tools/timeline", TimelineHandler,
)

