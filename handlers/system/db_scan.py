# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/12 23:04:00
# @modified 2021/10/02 21:14:19
import xutils
import xtemplate
import xauth
from xutils import dbutil
from xtemplate import BasePlugin

SCAN_HTML = """
<div class="card">
    <div class="card-title">
        <span>leveldb工具</span>

        <div class="float-right">
            {% include common/button/back_button.html %}
        </div>
    </div>
</div>

<div class="card">
    <form class="row">
        <div class="input-group">
            <label>数据库表</label>
            <select name="prefix" value="{{prefix}}">
                <option value="">全部</option>
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

            <div class="float-right btn-line-height">
                <a href="/fs_link/db">数据库目录</a>
            </div>
        </div>
    </form>
</div>

<div class="card">
    <table class="table">
        <tr>
            <th>主键</th>
            <th>值</th>
            <th><div class="float-right">操作</div></th>
        </tr>
        {% for key, value in result %}
            <tr>
                <td style="width:20%">{{key}}</td>
                <td style="width:60%">{{value}}</td>
                <td style="width:20%">
                    <div class="float-right">
                        <button class="btn btn-danger delete-btn" data-key="{{key}}">删除</button>
                    </div>
                </td>
            </tr>
        {% end %}
    </table>
</div>

<div class="card">
    <div class="pad5">
        <a href="?key_from={{last_key}}&prefix={{prefix}}&&db_key={{db_key}}">下一页</a>
    </div>
</div>

<script>
$(function () {
    $(".delete-btn").click(function (e) {
        var key = $(this).attr("data-key");
        xnote.confirm("准备删除【" + key + "】，请确认", function (confirmed) {
            var params = {key: key};
            $.post("?action=delete", params, function (resp) {
                window.location.reload();
            });
        });
    }); 
});
</script>

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

    @xauth.login_required("admin")
    def do_delete(self):
        key = xutils.get_argument("key", "")
        dbutil.delete(key)
        return dict(code = "success")
    
    def handle(self, input):
        action = xutils.get_argument("action", "")
        db_key = xutils.get_argument("db_key", "")
        prefix = xutils.get_argument("prefix", "")

        if action == "delete":
            return self.do_delete()

        result = []
        reverse  = xutils.get_argument("reverse") == "true"
        key_from = xutils.get_argument("key_from", "")
        last_key = [""]

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
