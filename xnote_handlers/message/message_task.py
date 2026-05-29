# encoding=utf-8

import typing
import xutils
import xnote_handlers.message.dao as msg_dao

from xutils import Storage
from xnote.core import xtemplate, xauth
from xnote.core.xnote_user_config import UserConfig
from xnote.core.xtemplate import T
from xnote_handlers.message.message_utils import list_task_tags
from xnote_handlers.message.message_utils import get_tags_from_message_list
from xnote_handlers.message.message_utils import is_marked_keyword
from xnote_handlers.message.message_utils import sort_keywords_by_marked, MessageListParser
from xnote_handlers.message.message_model import MessageTag, MessageTagEnum
from xnote_handlers.message.message_utils import MAX_LIST_LIMIT
from xnote_handlers.message.message_utils import filter_msg_list_by_keys, mark_filter_text
from xnote_handlers.message.message_template_service import handle_template_tab
from .message_tab import get_task_tab

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
                tag.custom_url = f"/message?tag=task&filterKey=$no_tag"
            else:
                tag.custom_url = f"/message?tag=task&filterKey={xutils.quote(tag.content)}"
    
    @classmethod
    def get_task_create_page(cls):
        filter_key = xutils.get_argument_str("filterKey")
        filter_tag1 = xutils.get_argument_str("filter_tag1")
        filter_tag2 = xutils.get_argument_str("filter_tag2")
        filter_tag3 = xutils.get_argument_str("filter_tag3")
        
        filter_keys = []
        if filter_key != "":
            filter_keys.append(filter_key)
        if filter_tag1 != "":
            filter_keys.append(filter_tag1)
        if filter_tag2 != "":
            filter_keys.append(filter_tag2)
        if filter_tag3 != "":
            filter_keys.append(filter_tag3)
        filter_key = ",".join(filter_keys)
        
        user_id = xauth.current_user_id()
        filter_content = UserConfig.task_filter.get_str(user_id)
        filter_config_key = UserConfig.task_filter.key
        user_name = xauth.current_name_str()

        show_side_tags = xutils.get_argument_bool("show_side_tags")
        kw = cls.get_task_kw()
        kw.show_input_box = True
        side_tags = list_task_tags(xauth.current_name_str())
        cls.fix_side_tags(side_tags)
        kw.side_tag_tab_key = "filterKey"
        kw.side_tags = side_tags
        kw.default_content = filter_key
        kw.search_type = "task"
        kw.search_placeholder = "搜索待办"
        kw.search_ext_dict = dict(tag = "task.search")
        kw.message_tag = "task"
        kw.filter_config_key = filter_config_key
        kw.filter_html = mark_filter_text(filter_content, link_type="task", selected_key=filter_key)
        kw.filter_key = filter_key

        if not show_side_tags:
            cls.hide_side_tags(kw)
            
        handle_template_tab(kw, "", template_type="task")
        kw.task_tab_component = get_task_tab(user_name, "task")
        
        return xtemplate.render("message/page/task_index.html", **kw)

    @classmethod
    def get_task_by_keyword_page(cls, filter_key):
        return cls.get_task_create_page()

    @classmethod
    def get_task_taglist_page(cls):
        user_name = xauth.current_name_str()
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
        kw.show_task_create_entry = True
        kw.show_task_done_entry = True
        kw.search_type = "task"
        kw.search_ext_dict = dict(tag="task.search")
        kw.task_tab_component = get_task_tab(user_name, "taglist")

        return xtemplate.render("message/page/task_tag_index.html", **kw)

    @classmethod
    def get_task_done_page(cls):
        user_name = xauth.current_name_str()
        kw = cls.get_task_kw()
        kw.show_input_box = False
        kw.message_tag = "done"
        kw.default_tab = "done"
        kw.task_tab_component = get_task_tab(user_name, "done")
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

        if page_name == "taglist":
            return TaskListHandler.get_task_taglist_page()

        if filter_key != "":
            return TaskListHandler.get_task_by_keyword_page(filter_key)
        else:
            # 任务的首页
            return TaskListHandler.get_task_create_page()


class TaskDoneHandler:
    @xauth.login_required()
    def GET(self):
        return TaskListHandler.get_task_done_page()

class TaskListAjaxHandler:

    @xauth.login_required()
    def GET(self):
        filter_key = xutils.get_argument_str("filterKey")
        quote_key = xutils.quote(filter_key)
        
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
        kw.page_url = f"?filterKey={quote_key}&page="

        return xtemplate.render("message/page/message_list_ajax.html", **kw)

    def do_list_task(self, user_name, offset, limit):
        p = xutils.get_argument_str("p", "")
        filter_key = xutils.get_argument_str("filterKey", "")

        if p == "done":
            return msg_dao.list_task_done(user_name, offset, limit)

        if filter_key != "":
            msg_list, amount = msg_dao.list_task(
                user_name, offset=0, limit=MAX_LIST_LIMIT)
            msg_list = filter_msg_list_by_keys(msg_list, filter_key.split(","))
            return msg_list[offset:offset+limit], len(msg_list)
        else:
            return msg_dao.list_task(user_name, offset, limit)

xurls = (
    r"/message/task", TaskHandler,
    r"/message/task/done", TaskDoneHandler,
    r"/message/task/list_ajax", TaskListAjaxHandler,
    r"/message/task/tag_list", TaskTagListPage,
)