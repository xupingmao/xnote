# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2021/03/06 12:12:12
import xauth
import xutils
import xmanager
from xutils import dbutil
from xtemplate import BasePlugin


HTML = """
<style>
    .key { width: 75%; }
    .admin-stat { margin-top: 10px; }
    .admin-stat-th { width: 25% }
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
            <th class="admin-stat-th">类别</th>
            <th class="admin-stat-th">项目</th>
            <th class="admin-stat-th">说明</th>
            <th class="admin-stat-th">数量</th>
        </tr>
        {% for category, key, description, value in admin_stat_list %}
            <tr>
                <td>{{category}}</td>
                <td><a href="/system/db_scan?prefix={{key}}&reverse=true">{{key}}</a></td>
                <td>{{description}}</td>
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

        xmanager.add_visit_log(user_name, "/note/stat")
        
        stat_list = []
        admin_stat_list = []
        stat_list.append(["我的项目", xutils.call("note.count_by_type", user_name, "group")])
        stat_list.append(["我的笔记", dbutil.count_table("note_tiny:%s" % user_name)])
        stat_list.append(["待办事项", dbutil.count_table("message:%s" % user_name)])
        stat_list.append(["搜索记录", dbutil.count_table("search_history:%s" % user_name)])
        stat_list.append(["我的评论", dbutil.count_table("comment_index:%s" % user_name)])
        
        if xauth.is_admin():
            table_dict = dbutil.get_table_dict_copy()
            table_values = sorted(table_dict.values(), key = lambda x:x.category)
            for table_info in table_values:
                name = table_info.name
                admin_stat_list.append([table_info.category, table_info.name, table_info.description, dbutil.count_table(name)])
        self.writetemplate(HTML, stat_list = stat_list, admin_stat_list = admin_stat_list)


xurls = (
    r"/note/stat", StatHandler
)