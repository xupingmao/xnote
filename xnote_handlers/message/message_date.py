# encoding=utf-8

import xutils
import xnote_handlers.message.dao as msg_dao

from xutils import Storage
from xutils import dateutil
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.plugin import TabBox
from xnote.core.xtemplate import T
from xnote_handlers.message.message_utils import MAX_LIST_LIMIT
from xnote_handlers.message.message_utils import filter_msg_list_by_key
from xnote_handlers.message.message_utils import do_split_date
from xnote_handlers.message.message_utils import convert_message_list_to_day_folder
from xnote_handlers.message.message_utils import count_month_size
from . import message_tag
from . import message_template_service
from .message_tab import get_message_log_tab

class MessageDateHandler:

    def do_list_by_date(self, user_name, date, offset, limit, tag=""):
        filter_key = xutils.get_argument_str("filterKey", "")

        if filter_key != "":
            msg_list, amount = msg_dao.list_by_date(
                user_name, date, 0, MAX_LIST_LIMIT, tag=tag)
            msg_list = filter_msg_list_by_key(msg_list, filter_key)
            return msg_list[offset:offset+limit], len(msg_list)
        else:
            return msg_dao.list_by_date(user_name, date, offset, limit, tag=tag)



def get_default_year_and_month():
    return dateutil.format_date(None, "%Y-%m")

class MessageListByDayHandler():

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        date = xutils.get_argument_str("date", "")
        show_empty = xutils.get_argument("show_empty", True, type=bool)

        if date == "":
            date = get_default_year_and_month()

        year, month, day = do_split_date(date)

        item_list, amount = msg_dao.list_by_date(
            user_name, date, limit=MAX_LIST_LIMIT, tag="log")
        message_list = convert_message_list_to_day_folder(
            item_list, date, True)
        
        kw = Storage()
        kw.tag = "log.date"
        kw.search_type = "message"
        kw.search_ext_dict = dict(tag="log.search")
        kw.tab_default = "log.date"
        kw.message_tab_component = get_message_log_tab(user_name, "log.date")

        return xtemplate.render("message/page/message_list_by_day.html",
                                date=date,
                                year=year,
                                month=month,
                                message_list=message_list,
                                show_empty=show_empty,
                                show_back_btn=True,
                                month_size=count_month_size(message_list),
                                **kw)


class CalendarHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        user_id = xauth.current_user_id()
        date = xutils.get_argument_str("date")

        year, month, mday = do_split_date(date)

        date = "%s-%02d" % (year, month)

        filter_tab = TabBox(tab_key="filterKey", tab_default="", title="标签", css_class="btn-style")
        filter_tab.add_tab(title="全部", value="", href=f"/message/calendar?date={date}")

        tag_list = message_tag.get_tag_list_by_month(user_id=user_id, month=date, tag="log")
        for tag_info in tag_list:
            filter_tab.add_tab(title=tag_info.name, value=tag_info.name)

        kw = Storage()
        kw.tag = "log.date"
        kw.year = year
        kw.month = month
        kw.date = date
        kw.html_title = T("随手记")
        kw.search_type = "message"
        kw.filter_tab = filter_tab
        kw.tab_default = "log.date"
        kw.message_tab_component = get_message_log_tab(user_name, "log.date")
        
        # 实际数据从 /message/date 接口获取

        return xtemplate.render("message/page/message_calendar.html", **kw)


class DateDetailHandler:
    
    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        date = xutils.get_argument_str("date")
        kw = Storage()
        kw.message_placeholder = f"补充{date}发生的事情"

        filter_key = xutils.get_argument_str("filterKey", "")
        if filter_key != "":
            kw.show_input_box = False
        
        kw.message_left_class = "hide"
        kw.message_right_class = "row"
        kw.show_side_tags = False
        kw.tab_default = "log.date"
        kw.tag = "log"
        kw.message_tag = "log.date"
        kw.create_date = date
        kw.message_tab_component = get_message_log_tab(user_name, "log.date")

        message_template_service.handle_template_tab(kw, default_content="")

        return xtemplate.render("message/page/message_list_view.html",
                                search_type="message",
                                html_title=T("随手记"),
                                show_back_btn=True,
                                **kw)

xurls = (
    # 日记
    r"/message/diary", MessageListByDayHandler,
    r"/message/list_by_day", MessageListByDayHandler,
    r"/message/calendar", CalendarHandler,
    r"/message/date_detail", DateDetailHandler,
)