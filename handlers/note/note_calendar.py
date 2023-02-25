# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/12/17 23:18:20
# @modified 2020/12/17 23:25:30
import xmanager
import xauth
import xtemplate

class NoteCalendarHandler:
    """日历视图"""

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name_str()
        xmanager.add_visit_log(user, "/note/calendar")

        return xtemplate.render("note/page/note_calendar.html")


xurls = (
    r"/note/calendar", NoteCalendarHandler,
)

