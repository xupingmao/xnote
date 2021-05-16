# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/12 23:04:00
# @modified 2021/05/16 23:49:42
import xutils
import xtemplate
from xutils import dbutil
from xtemplate import BasePlugin

SCAN_HTML = """
<div class="card">
    <div class="card-title">
        <span>数据库工具</span>

        <div class="float-right">
            {% include common/button/back_button.html %}
        </div>
    </div>

    <form class="row">
        <div class="input-group">
            <label>数据库表</label>
            <select name="prefix" value="{{prefix}}">
                <option value="*">全部</option>
                {% for key in table_dict %}
                    <option value="{{key}}">{{key}}</option>
                {% end %}
            </select>
        </div>

        <div class="input-group">
            <label>关键字</label>
            <input name="db_key" value="{{db_key}}"/>
        </div>

        <div class="input-group">
            <button type="submit">查询</button>
        </div>
    </form>
</div>

<div class="card">
    <table class="table">
        <tr>
            <th>主键</th>
            <th>值</th>
            <th>操作</th>
        </tr>
        {% for key, value in result %}
            <tr>
                <td style="width:20%">{{key}}</td>
                <td style="width:60%">{{value}}</td>
                <td style="width:20%"></td>
            </tr>
        {% end %}
    </table>
    <a href="?key_from={{last_key}}&prefix={{prefix}}&&db_key={{db_key}}">下一页</a>
</div>
"""

class DbScanHandler(BasePlugin):

    title = "数据库工具"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = "system"

    placeholder = "主键"
    btn_text = "查询"
    editable = False
    show_search = False
    show_title = False

    rows = 0
    
    def handle(self, input):
        db_key = xutils.get_argument("db_key", "")
        prefix = xutils.get_argument("prefix", "")

        result = []
        reverse  = xutils.get_argument("reverse") == "true"
        key_from = xutils.get_argument("key_from", "")
        last_key = [None]

        def func(key, value):
            # print("db_scan:", key, value)
            if db_key in value:
                result.append((key, value))
                if len(result) > 30:
                    last_key[0] = key
                    return False
            return True

        if prefix != "" and prefix != None:
            dbutil.prefix_scan(prefix, func, reverse = reverse, parse_json = False)
        else:
            dbutil.scan(key_from = key_from, func = func, reverse = reverse)

        self.writetemplate(SCAN_HTML, 
            result = result, 
            table_dict = dbutil.get_table_dict_copy(), 
            prefix = prefix,
            db_key = db_key,
            last_key = last_key[0]
        )



xurls = (
    "/system/db_scan", DbScanHandler
)
