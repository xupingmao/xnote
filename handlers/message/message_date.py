# encoding=utf-8

import xutils
import handlers.message.dao as msg_dao

from xutils import Storage
from xutils import dateutil
from xnote.core import xauth
from xnote.core import xtemplate
from handlers.message.message_utils import MAX_LIST_LIMIT
from handlers.message.message_utils import filter_msg_list_by_key
from handlers.message.message_utils import do_split_date
from handlers.message.message_utils import convert_message_list_to_day_folder
from handlers.message.message_utils import count_month_size

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
        user_name = xauth.current_name()
        date = xutils.get_argument("date", "")
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

        return xtemplate.render("message/page/message_list_by_day.html",
                                date=date,
                                year=year,
                                month=month,
                                message_list=message_list,
                                show_empty=show_empty,
                                show_back_btn=True,
                                month_size=count_month_size(message_list),
                                **kw)
