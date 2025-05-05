# encoding=utf-8

import typing
import xutils
import handlers.message.dao as msg_dao

from xutils import Storage
from xnote.core import xtemplate, xauth
from xnote.core.xtemplate import T
from handlers.message.message_utils import list_task_tags
from handlers.message.message_utils import get_tags_from_message_list
from handlers.message.message_utils import is_marked_keyword
from handlers.message.message_utils import sort_keywords_by_marked, MessageListParser
from handlers.message.message_model import MessageTag, MessageTagEnum
from handlers.message.message_utils import MAX_LIST_LIMIT
from handlers.message.message_utils import filter_msg_list_by_key

class TaskListHandler:

    @classmethod
    def hide_side_tags(cls, kw: Storage):
        kw.show_side_tags = False
        kw.message_left_class = "hide"
        kw.message_right_class = "row"
    
    @staticmethod
    def get_task_kw():
        kw = Storage()
        kw.title = T("待办任务")
        kw.html_title = T("待办任务")
        kw.search_type = "task"
        kw.show_back_btn = True
        kw.tag = "task"
        kw.message_placeholder = T("添加待办任务")
        kw.message_tab = "task"
        return kw
    
    @classmethod
    def fix_side_tags(cls, side_tags: typing.List[MessageTag]):
        for tag in side_tags:
            if tag.is_no_tag:
                tag.customized_url = f"/message?tag=task&filterKey=$no_tag"
            else:
                tag.customized_url = f"/message?tag=task&filterKey={xutils.quote(tag.content)}"
    
    @classmethod
    def get_task_create_page(cls):
        show_side_tags = xutils.get_argument_bool("show_side_tags")
        kw = cls.get_task_kw()
        kw.show_input_box = True
        kw.show_system_tag = False
        side_tags = list_task_tags(xauth.current_name_str())
        cls.fix_side_tags(side_tags)
        kw.side_tag_tab_key = "filterKey"
        kw.side_tags = side_tags
        kw.default_content = xutils.get_argument_str("filterKey")
        kw.search_type = "task"
        kw.search_placeholder = "搜索待办"
        kw.search_ext_dict = dict(tag = "task.search")
        kw.message_tag = "task"

        if not show_side_tags:
            cls.hide_side_tags(kw)
        
        return xtemplate.render("message/page/task_index.html", **kw)

    @classmethod
    def get_task_by_keyword_page(cls, filter_key):
        return cls.get_task_create_page()

    @classmethod
    def get_task_taglist_page(cls):
        user_name = xauth.current_name()
        msg_list, amount = msg_dao.list_task(user_name, 0, 1000)

        tag_list = get_tags_from_message_list(
            msg_list, "task", display_tag="taglist", search_tag="task")

        for tag in tag_list:
            is_marked = is_marked_keyword(user_name, tag.tag_code)
            tag.set_is_marked(is_marked)

        sort_keywords_by_marked(tag_list)

        kw = cls.get_task_kw()
        kw.date = ""
        kw.tag_list = tag_list
        kw.html_title = T("待办任务")
        kw.message_placeholder = T("添加待办任务")

        kw.show_sub_link = False
        kw.show_task_create_entry = True
        kw.show_task_done_entry = True
        kw.search_type = "task"
        kw.search_ext_dict = dict(tag="task.search")

        return xtemplate.render("message/page/task_tag_index.html", **kw)

    @classmethod
    def get_task_done_page(cls):
        kw = cls.get_task_kw()
        kw.show_system_tag = False
        kw.show_input_box = False
        kw.message_tag = "done"
        cls.hide_side_tags(kw)
        return xtemplate.render("message/page/task_done_index.html", **kw)


class TaskTagListPage:

    @xauth.login_required()
    def GET(self):
        return TaskListHandler.get_task_taglist_page()


class TaskHandler:
    @xauth.login_required()
    def GET(self):
        filter_key = xutils.get_argument_str("filterKey", "")
        page_name = xutils.get_argument_str("p", "")

        if page_name == "create":
            return TaskListHandler.get_task_create_page()

        if page_name == "done":
            return TaskListHandler.get_task_done_page()

        if page_name == "taglist":
            return TaskListHandler.get_task_taglist_page()

        if filter_key != "":
            return TaskListHandler.get_task_by_keyword_page(filter_key)
        else:
            # 任务的首页
            return TaskListHandler.get_task_create_page()

class TaskListAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        limit = 20
        page = xutils.get_argument_int("page", default_value=1)
        offset = (page-1) * limit
        chatlist, amount = self.do_list_task(user_name, offset=offset, limit=limit)

        parser = MessageListParser(chatlist, tag=MessageTagEnum.task.value)
        parser.parse()
        chatlist = parser.get_message_list()

        kw = Storage()
        kw.page = page
        kw.page_total = amount
        kw.item_list = chatlist

        return xtemplate.render("message/page/message_list_ajax.html", **kw)

    def do_list_task(self, user_name, offset, limit):
        p = xutils.get_argument_str("p", "")
        filter_key = xutils.get_argument("filterKey", "")

        if p == "done":
            return msg_dao.list_task_done(user_name, offset, limit)

        if filter_key != "":
            msg_list, amount = msg_dao.list_task(
                user_name, offset=0, limit=MAX_LIST_LIMIT)
            msg_list = filter_msg_list_by_key(msg_list, filter_key)
            return msg_list[offset:offset+limit], len(msg_list)
        else:
            return msg_dao.list_task(user_name, offset, limit)

xurls = (
    r"/message/task", TaskHandler,
    r"/message/task/list_ajax", TaskListAjaxHandler,
    r"/message/task/tag_list", TaskTagListPage,
)