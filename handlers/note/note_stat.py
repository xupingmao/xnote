# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2022/04/20 23:03:49
import xauth
import xutils
import xmanager
from xutils import dbutil
from xtemplate import BasePlugin
import handlers.message.dao as msg_dao
import handlers.note.dao as note_dao

HTML = """
<style>
    .key { width: 75%; }
    .admin-stat-th { width: 25% }
</style>

{% if stat_list != None %}
<div class="card">
    <table class="table">
        <tr>
            <th class="key">项目</th>
            <th>数量</th>
        </tr>
        {% for key, value in stat_list %}
            <tr>
                <td>{{key}}</td>
                <td>{{value}}</td>
            </tr>
        {% end %}
    </table>
</div>
{% end %}
"""

SIDEBAR_HTML = """
{% include note/component/sidebar/group_list_sidebar.html %}
"""

class StatHandler(BasePlugin):

    title = "数据统计"
    editable = False
    require_admin = False
    rows = 0

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

    def get_admin_stat_list(self, hide_index):
        admin_stat_list = []
        if xauth.is_admin():
            table_dict = dbutil.get_table_dict_copy()
            table_values = sorted(table_dict.values(), key = lambda x:(x.category,x.name))
            for table_info in table_values:
                name = table_info.name
                if hide_index == "true" and name.startswith("_index"):
                    continue
                admin_stat_list.append([table_info.category, 
                    table_info.name, 
                    table_info.description, 
                    dbutil.count_table(name, use_cache = True)])
        return admin_stat_list

    def handle(self, input):
        p = xutils.get_argument("p", "")
        hide_index = xutils.get_argument("hide_index", "true")
        user_name = xauth.current_name()
        assert isinstance(user_name, str)

        xmanager.add_visit_log(user_name, "/note/stat")
        
        if p == "system":
            stat_list = None
            admin_stat_list = self.get_admin_stat_list(hide_index)
        else:
            stat_list = self.get_stat_list(user_name)
            admin_stat_list = self.get_admin_stat_list(hide_index)
        
        self.writetemplate(HTML, stat_list = stat_list, admin_stat_list = admin_stat_list)
        self.write_aside(SIDEBAR_HTML)

xurls = (
    r"/note/stat", StatHandler,
)