# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/08/20 11:02:04
# @modified 2019/08/20 11:10:15
import xauth
from xutils import dbutil
from xtemplate import BasePlugin


HTML = """
<table class="table">
    <tr>
        <th>项目</th>
        <th>数量</th>
    </tr>
    {% for key, value in stat_list %}
        <tr>
            <td>{{key}}</td>
            <td>{{value}}</td>
        </tr>
    {% end %}

</table>
"""

class StatHandler(BasePlugin):

    title = "笔记数据统计"
    editable = False

    def handle(self, input):
        self.rows = 0
        user_name = xauth.current_name()
        stat_list = []
        stat_list.append(["笔记总数", dbutil.count_table("note_tiny:%s" % user_name)])
        stat_list.append(["备忘总数", dbutil.count_table("message:%s" % user_name)])

        self.writetemplate(HTML, stat_list = stat_list)


xurls = (
    r"/note/stat", StatHandler
)