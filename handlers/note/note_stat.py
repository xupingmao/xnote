# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2019/11/11 21:09:36
import xauth
import xutils
from xutils import dbutil
from xtemplate import BasePlugin


HTML = """
<style>
    .key { width: 75%; }
    .admin-stat { margin-top: 10px; }
</style>

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

{% if _is_admin %}
    <h3 class="card-title admin-stat">全局统计</h3>
    <table class="table">
        <tr>
            <th class="key">项目</th>
            <th>数量</th>
        </tr>
        {% for key, value in admin_stat_list %}
            <tr>
                <td>{{key}}</td>
                <td>{{value}}</td>
            </tr>
        {% end %}
    </table>
{% end %}
"""

class StatHandler(BasePlugin):

    title = "数据统计"
    editable = False
    require_admin = False

    def handle(self, input):
        self.rows = 0
        user_name = xauth.current_name()
        stat_list = []
        admin_stat_list = []
        stat_list.append(["我的笔记", dbutil.count_table("note_tiny:%s" % user_name)])
        stat_list.append(["笔记本",   xutils.call("note.count_by_type", user_name, "group")])
        stat_list.append(["备忘总数", dbutil.count_table("message:%s" % user_name)])
        if xauth.is_admin():
            admin_stat_list.append(["note_full", dbutil.count_table("note_full")])
            admin_stat_list.append(["note_tiny", dbutil.count_table("note_tiny")])
            admin_stat_list.append(["note_index", dbutil.count_table("note_index")])
            admin_stat_list.append(["note_history", dbutil.count_table("note_history")])
            admin_stat_list.append(["note_comment", dbutil.count_table("note_comment")])
            admin_stat_list.append(["notebook", dbutil.count_table("notebook")])
            admin_stat_list.append(["message",  dbutil.count_table("message")])
            admin_stat_list.append(["schedule", dbutil.count_table("schedule")])
            admin_stat_list.append(["user", dbutil.count_table("user")])

        self.writetemplate(HTML, stat_list = stat_list, admin_stat_list = admin_stat_list)


xurls = (
    r"/note/stat", StatHandler
)