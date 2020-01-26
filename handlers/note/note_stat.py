# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2020/01/26 12:55:59
import xauth
import xutils
from xutils import dbutil
from xtemplate import BasePlugin


HTML = """
<style>
    .key { width: 75%; }
    .admin-stat { margin-top: 10px; }
</style>

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

{% if _is_admin %}
<div class="card">
    <h3 class="card-title admin-stat">全局统计</h3>
    <table class="table">
        <tr>
            <th class="key">项目</th>
            <th>数量</th>
        </tr>
        {% for key, value in admin_stat_list %}
            <tr>
                <td><a href="/system/db_scan?prefix={{key}}&reverse=true">{{key}}</a></td>
                <td>{{value}}</td>
            </tr>
        {% end %}
    </table>
</div>
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
        stat_list.append(["我的项目", xutils.call("note.count_by_type", user_name, "group")])
        stat_list.append(["我的笔记", dbutil.count_table("note_tiny:%s" % user_name)])
        stat_list.append(["待办事项", dbutil.count_table("message:%s" % user_name)])
        stat_list.append(["搜索记录", dbutil.count_table("search_history:%s" % user_name)])
        stat_list.append(["我的评论", dbutil.count_table("comment_index:%s" % user_name)])
        
        if xauth.is_admin():
            admin_stat_list.append(["note_full", dbutil.count_table("note_full")])
            admin_stat_list.append(["note_tiny", dbutil.count_table("note_tiny")])
            admin_stat_list.append(["note_index", dbutil.count_table("note_index")])
            admin_stat_list.append(["note_history", dbutil.count_table("note_history")])
            admin_stat_list.append(["note_comment", dbutil.count_table("note_comment")])
            admin_stat_list.append(["comment_index", dbutil.count_table("comment_index")])
            admin_stat_list.append(["note_deleted", dbutil.count_table("note_deleted")])
            admin_stat_list.append(["notebook", dbutil.count_table("notebook")])
            admin_stat_list.append(["search_history", dbutil.count_table("search_history")])
            admin_stat_list.append(["message",  dbutil.count_table("message")])
            admin_stat_list.append(["msg_search_history", dbutil.count_table("msg_search_history")])
            admin_stat_list.append(["msg_history", dbutil.count_table("msg_history")])
            admin_stat_list.append(["msg_key", dbutil.count_table("msg_key")])
            admin_stat_list.append(["user_stat", dbutil.count_table("user_stat")])

            admin_stat_list.append(["schedule", dbutil.count_table("schedule")])
            admin_stat_list.append(["user", dbutil.count_table("user")])
            admin_stat_list.append(["record", dbutil.count_table("record")])

        self.writetemplate(HTML, stat_list = stat_list, admin_stat_list = admin_stat_list)


xurls = (
    r"/note/stat", StatHandler
)