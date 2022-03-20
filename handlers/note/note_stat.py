# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2022/03/20 13:20:25
import xauth
import xutils
import xmanager
from xutils import dbutil
from xtemplate import BasePlugin

MSG_DAO = xutils.DAO("message")

HTML = """
<style>
    .key { width: 75%; }
    .admin-stat-th { width: 25% }
</style>

{% include system/component/db_nav.html %}

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

{% if _is_admin %}
<div class="card admin-stat">
    <div class="card-title"> 
        <span>全局统计</span>

        <div class="float-right">
            {% if hide_index != "true" %}
                <a class="btn btn-default" href="?p={{p}}&hide_index=true">隐藏索引</a>
            {% else %}
                <a class="btn btn-default" href="?p={{p}}">展示索引</a>
            {% end %}
        </div>
    </div>
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
    rows = 0

    def get_stat_list(self, user_name):
        stat_list = []
        message_stat = MSG_DAO.get_message_stat(user_name)
        stat_list.append(["我的笔记本", xutils.call("note.count_by_type", user_name, "group")])
        stat_list.append(["我的笔记", dbutil.count_table("note_tiny:%s" % user_name)])
        stat_list.append(["我的待办", message_stat.task_count])
        stat_list.append(["我的记事", message_stat.log_count])
        stat_list.append(["搜索记录", dbutil.count_table("search_history:%s" % user_name)])
        stat_list.append(["我的评论", dbutil.count_table("comment_index:%s" % user_name)])
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
        hide_index = xutils.get_argument("hide_index", "")
        user_name = xauth.current_name()

        xmanager.add_visit_log(user_name, "/note/stat")
        
        if p == "system":
            stat_list = None
            admin_stat_list = self.get_admin_stat_list(hide_index)
        else:
            stat_list = self.get_stat_list(user_name)
            admin_stat_list = self.get_admin_stat_list(hide_index)
        
        self.writetemplate(HTML, stat_list = stat_list, admin_stat_list = admin_stat_list)


xurls = (
    r"/note/stat", StatHandler
)