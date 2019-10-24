# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2019/10/23 01:33:08
import xauth
import xutils
from xutils import dbutil
from xtemplate import BasePlugin


HTML = """
<style>
    .key { width: 75%; }
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
    <h3>全局统计</h3>
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

    title = "笔记数据统计"
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
            admin_stat_list.append(["笔记总数", dbutil.count_table("note_tiny")])
            admin_stat_list.append(["笔记历史数", dbutil.count_table("note_history")])
            admin_stat_list.append(["评论总数", dbutil.count_table("note_comment")])
            admin_stat_list.append(["notebook", dbutil.count_table("notebook")])

        self.writetemplate(HTML, stat_list = stat_list, admin_stat_list = admin_stat_list)


xurls = (
    r"/note/stat", StatHandler
)