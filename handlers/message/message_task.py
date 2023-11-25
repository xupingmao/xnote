# encoding=utf-8

import xutils
from xutils import Storage
from xnote.core import xtemplate, xauth
from xnote.core.xtemplate import T
from handlers.message.message_utils import list_task_tags

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

