# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2022/04/20 23:03:49
import xnote_handlers.message.dao as msg_dao
import xnote_handlers.note.dao as note_dao

from typing import List
from xnote.core import xauth
from xnote.core import xmanager
from xnote.core import xconfig
from xnote.service import SearchHistoryService, SearchHistoryType
from xutils import dbutil, Storage
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.webui import ListView, ListViewItem
from xnote.plugin import find_plugin, iter_plugins
from xnote_handlers.config import LinkConfig


class StatInfo(Storage):
    def __init__(self, title="", amount=0, url=""):
        super(StatInfo).__init__()
        self.title = title
        self.amount = amount
        self.url = xconfig.WebConfig.resolve_path(url)
    
class StatHandler(BaseTablePlugin):

    title = "数据统计"
    editable = False
    require_admin = False
    rows = 0
    parent_link = LinkConfig.app_index

    BODY_HTML = """
    {% init admin_table = None %}
    <div class="card">
        {% render user_table %}
    </div>
    {% if admin_table %}
        <div class="card">
            <h3 class="card-title">后台统计数据</h3>
            {% render admin_table %}
        </div>
    {% end %}
"""
    SIDEBAR_HTML = """
{% include note/component/sidebar/group_list_sidebar.html %}
"""

    def get_stat_list(self, user_name):
        user_id = xauth.UserDao.get_id_by_name(user_name)
        stat_list: List[StatInfo] = []
        message_stat = msg_dao.get_message_stat(user_name)
        note_stat = note_dao.get_note_stat(user_name)
        group_count = note_stat.group_count
        note_count = note_stat.total
        comment_count = note_stat.comment_count
        search_count = SearchHistoryService.count(user_id=user_id, search_type=SearchHistoryType.default)

        stat_list.append(StatInfo("我的笔记本", group_count, url="/note/group_list"))
        stat_list.append(StatInfo("我的笔记", note_count, url="/note/group/year"))
        stat_list.append(StatInfo("我的待办", message_stat.task_count, url="/message/task"))
        stat_list.append(StatInfo("已完成任务", message_stat.done_count, url="/message/task/done"))
        stat_list.append(StatInfo("我的记事", message_stat.log_count, url="/message"))
        stat_list.append(StatInfo("搜索记录", search_count, url="/search/history"))
        stat_list.append(StatInfo("我的评论", comment_count, url="/note/comment/mine"))
        
        return stat_list
    
    def create_list(self):
        return ListView()
    
    def get_admin_table(self):
        list_view = self.create_list()
        plugin_count = 0
        external_plugin_count = 0
        for plugin in iter_plugins():
            plugin_count += 1
            if plugin.is_external:
                external_plugin_count += 1

        list_view.add_item(ListViewItem(text="全部插件", href="/plugin_list", badge_info=str(plugin_count), show_chevron_right=True))
        list_view.add_item(ListViewItem(text="第三方插件", href="/plugin_list", badge_info=str(external_plugin_count), show_chevron_right=True))
        return list_view
        
    def get_user_table(self, user_name=""):
        list_view = self.create_list()
        for stat_info in self.get_stat_list(user_name):
            list_item = ListViewItem(text=stat_info.title, href=stat_info.url, badge_info=str(stat_info.amount))
            list_item.show_chevron_right = True
            list_view.add_item(list_item)
        return list_view

    def handle(self, input=""):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/note/stat")
        
        
        kw = Storage()
        kw.user_table = self.get_user_table(user_name)
        if xauth.is_admin():
            kw.admin_table = self.get_admin_table()
        
        self.writehtml(self.BODY_HTML, **kw)
        self.write_aside(self.SIDEBAR_HTML)

xurls = (
    r"/note/stat", StatHandler,
)