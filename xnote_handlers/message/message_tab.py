from xnote.plugin import TabBox
from .dao import get_message_stat
from .message_model import MessageTagEnum

def get_message_log_tab(user: str, tab_default="log"):
    stat = get_message_stat(user)
    tab = TabBox(tab_key="tag", tab_default=tab_default, css_class="card message-tab")
    tab.add_item(f"记事({stat.log_count})", value="log", href="/message?tag=log")
    tab.add_item(f"标签({stat.key_count})", value="log.tags", href="/message/tag/list")
    tab.add_item(f"日期", value="log.date", href="/message/diary?tag=log.date")
    return tab


def get_task_tab(user: str, tab_default="task"):
    stat = get_message_stat(user)
    tab = TabBox(tab_key="p", tab_default=tab_default, css_class="card message-tab")
    tab.add_item(f"待办({stat.task_count})", value="task", href="/message/task")
    tab.add_item(f"已完成({stat.done_count})", value="done", href="/message/task/done")
    tab.add_item(f"标签", value="taglist", href="/message/task/tag_list")
    return tab

def get_system_tag_tabs(tab_default=""):
    tab = TabBox(tab_key="tag_code", tab_default=tab_default, title="系统标签", css_class="card btn-style")
    tab.add_item(title="全部", value="", href="/message/tag/list")
    for item in MessageTagEnum.system_tag_list:
        tab.add_item(title=item.name, value=item.value, href=item.url)
    return tab
