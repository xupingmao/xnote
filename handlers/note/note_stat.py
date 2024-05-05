# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2022/04/20 23:03:49
from xnote.core import xauth
from xnote.core import xmanager
from xutils import dbutil
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import DataTable
import handlers.message.dao as msg_dao
import handlers.note.dao as note_dao

class StatHandler(BaseTablePlugin):

    title = "数据统计"
    editable = False
    require_admin = False
    rows = 0

    BODY_HTML = """
    <div class="card">
        {% include common/table/table.html %}
    </div>
"""
    SIDEBAR_HTML = """
{% include note/component/sidebar/group_list_sidebar.html %}
"""

    def get_stat_list(self, user_name):
        stat_list = []
        message_stat = msg_dao.get_message_stat(user_name)
        note_stat = note_dao.get_note_stat(user_name)
        group_count = note_stat.group_count
        note_count = note_stat.total
        comment_count = note_stat.comment_count
        search_count = dbutil.count_table("search_history:%s" % user_name, use_cache=True)

        stat_list.append(["我的笔记本", group_count])
        stat_list.append(["我的笔记", note_count])
        stat_list.append(["我的待办", message_stat.task_count])
        stat_list.append(["我的记事", message_stat.log_count])
        stat_list.append(["搜索记录", search_count])
        stat_list.append(["我的评论", comment_count])
        return stat_list

    def handle(self, input=""):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/note/stat")
        
        table = DataTable()
        table.add_head("项目", width="60%", field="key")
        table.add_head("数量", width="40%", field="value")

        for key, value in self.get_stat_list(user_name):
            row = dict(key=key, value=value)
            table.add_row(row)
        
        self.writehtml(self.BODY_HTML, table=table)
        self.write_aside(self.SIDEBAR_HTML)

xurls = (
    r"/note/stat", StatHandler,
)