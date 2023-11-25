# encoding=utf-8

import xutils
from xutils import Storage
from xnote.core import xtemplate, xauth
from xnote.core.xtemplate import T
import handlers.message.dao as msg_dao
from handlers.message.message_utils import list_task_tags, get_tags_from_message_list, is_marked_keyword, sort_keywords_by_marked

class TaskListHandler:
    
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
    def get_task_create_page(cls):
        kw = cls.get_task_kw()
        kw.show_input_box = True
        kw.show_system_tag = False
        side_tags = list_task_tags(xauth.current_name())
        for tag in side_tags:
            tag.url = f"/message?tag=task&filterKey={xutils.quote(tag.content)}"
        kw.side_tag_tab_key = "filterKey"
        kw.side_tags = side_tags
        kw.default_content = xutils.get_argument_str("filterKey")
        kw.search_type = "task"
        kw.search_placeholder = "搜索待办"
        kw.search_ext_dict = dict(tag = "task.search")
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
            tag.is_marked = is_marked_keyword(user_name, tag.name)

        sort_keywords_by_marked(tag_list)

        kw = cls.get_task_kw()
        kw.tag_list = tag_list
        kw.html_title = T("待办任务")
        kw.message_placeholder = T("添加待办任务")

        kw.show_sub_link = False
        kw.show_task_create_entry = True
        kw.show_task_done_entry = True
        kw.search_type = "task"
        kw.search_ext_dict = dict(tag="task.search")

        return xtemplate.render("message/page/message_tag_view.html", **kw)

    @classmethod
    def get_task_done_page(cls):
        kw = cls.get_task_kw()
        kw.show_system_tag = False
        kw.show_input_box = False
        kw.show_side_tags = False
        return xtemplate.render("message/page/message_list_view.html", **kw)
