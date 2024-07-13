# encoding=utf-8

import xutils
import handlers.message.dao as msg_dao


from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core.xtemplate import T
from handlers.message.message_tag import MAX_LIST_LIMIT
from handlers.message.message_utils import get_tags_from_message_list
from handlers.message.message_utils import do_split_date

class MonthTagsPage:
    
    def do_get(self):
        user_name = xauth.current_name()
        date = xutils.get_argument_str("date")

        year, month, mday = do_split_date(date)

        msg_list, amount = msg_dao.list_by_date(
            user_name, date, limit=MAX_LIST_LIMIT)

        tag_list = get_tags_from_message_list(msg_list, "date", date)

        return xtemplate.render("message/page/task_tag_index.html",
                                year=year,
                                month=month,
                                message_tag="calendar",
                                search_type="message",
                                show_back_btn=True,
                                tag_list=tag_list,
                                html_title=T("待办任务"),
                                message_placeholder="添加待办任务")

