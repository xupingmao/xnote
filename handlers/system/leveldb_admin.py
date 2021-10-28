# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/12 23:04:00
# @modified 2021/10/29 00:26:30
import xutils
import xtemplate
import xauth
from xutils import dbutil
from xutils import Storage
from xtemplate import BasePlugin

SCAN_HTML = """
<style>
    .value-detail {
        width:100%;
        height:95%;
    }
</style>

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
                    <option value="{{key+':'}}">{{key}}</option>
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

{% if error != "" %}
    <div class="card error">
        <div class="col-md-12 error">
            {{error}}
        </div>
    </div>
{% end %}

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
                <td style="width:60%">{{get_display_value(value)}}</td>
                <td style="width:20%">
                    <div class="float-right">
                        <button class="btn btn-default view-btn" data-key="{{key}}" data-value="{{value}}">查看</button>
                        <button class="btn btn-danger delete-btn" data-key="{{key}}">删除</button>
                    </div>
                </td>
            </tr>
        {% end %}
    </table>
</div>

<div class="card">
    <div class="pad5 align-center">
        <a href="?key_from={{last_key}}&prefix={{prefix}}&&db_key={{db_key}}&reverse={{reverse}}">下一页</a>
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

    $(".view-btn").click(function (e) {
        var value = $(this).attr("data-value");
        var text = $("<textarea>").text(value).addClass("value-detail");
        xnote.showDialog("数据详情", text.prop("outerHTML"));
    }); 
});
</script>

"""

def get_display_value(value):
    if value is None:
        return value

    if len(value) > 100:
        return value[:100] + "..."
    return value

def parse_bool(value):
    return value == "true"

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
        reverse = xutils.get_argument("reverse", "")
        key_from = xutils.get_argument("key_from", "")

        if action == "delete":
            return self.do_delete()

        result = []
        need_reverse = parse_bool(reverse)
        max_scan = 1000
        self.scan_count = 0
        self.error = ""
        self.last_key = ""

        def func(key, value):
            # print("db_scan:", key, value)
            self.scan_count += 1
            if self.scan_count > max_scan:
                self.error = "too many scan"
                return False

            if not key.startswith(prefix):
                return False

            if db_key in value:
                result.append((key, value))
                if len(result) > 30:
                    return False
            
            self.last_key = key
            return True

        if key_from == "" and prefix == "":
            key_from = ""

        if key_from == "" and prefix != "":
            key_from = prefix

        dbutil.scan(key_from = key_from, func = func, reverse = need_reverse, parse_json = False)

        kw = Storage()
        kw.result = result
        kw.table_dict = dbutil.get_table_dict_copy()
        kw.prefix = prefix
        kw.db_key = db_key
        kw.reverse = reverse
        kw.get_display_value = get_display_value
        kw.error = self.error
        kw.last_key = self.last_key

        self.writetemplate(SCAN_HTML, **kw)



xurls = (
    "/system/db_scan", DbScanHandler,
    "/system/leveldb_admin", DbScanHandler,
)
