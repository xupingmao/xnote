# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/12 23:04:00
# @modified 2022/03/19 18:54:15
import xutils
import xauth
from xutils import dbutil
from xutils import Storage
from xtemplate import BasePlugin
from xutils import textutil

SCAN_HTML = """
<style>
    .value-detail {
        width:100%;
        height:95%;
    }
</style>

{% include system/component/db_nav.html %}

<div class="card">
    <form>
        <div class="row">
            <div class="input-group">
                <label>数据库表</label>
                <select name="prefix" value="{{prefix}}">
                    <option value="">全部</option>
                    {% for key in table_names %}
                        <option value="{{key}}">{{key}}</option>
                    {% end %}
                </select>
            </div>

            <div class="input-group">
                <label>用户</label>
                <input name="q_user_name" value="{{q_user_name}}" type="text"/>
            </div>

            <div class="input-group">
                <label>关键字</label>
                <input name="db_key" value="{{db_key}}" type="text"/>
            </div>
        </div>

        <div class="row">
            <div class="align-center">
                <input type=checkbox name="reverse" {% if is_reverse %}checked{%end%}><span>倒序</span>
                <input type="button" class="do-search-btn" value="查询数据">
                <a class="btn btn-default" href="?p=query&prefix={{prefix}}&reverse=true">重置查询</a>
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

<div class="result-rows">
    <!-- 搜索结果 -->
</div>

<div class="card hide">
    <div class="pad5 align-center">
        <a href="?key_from={{quote(last_key)}}&prefix={{prefix}}&&db_key={{quote(db_key)}}&q_user_name={{q_user_name}}">下一页</a>
    </div>
</div>

<!-- 模板 -->
<script type="text/template" id="result-rows-template">
<div class="card btn-line-height">
    <span>扫描行数: {{!scanned}}</span>
    <span>匹配行数: {{!result.length}}</span>
</div>

<div class="card">
    <table class="table">
        <tr>
            <th>主键</th>
            <th>值</th>
            <th><div class="float-right">操作</div></th>
        </tr>
        {{! each result item }}
            <tr>
                <td style="width:20%">{{!item.key}}</td>
                <td style="width:60%">{{!item.valueShort}}</td>
                <td style="width:20%">
                    <div class="float-right">
                        <button class="btn btn-default view-btn" data-key="{{!item.key}}" 
                            data-value="{{!item.value}}">查看</button>
                        <button class="btn btn-danger delete-btn" data-key="{{!item.key}}">删除</button>
                    </div>
                </td>
            </tr>
        {{!/each }}
    </table>
</div>
</script>

<script>
$(function () {
    var globalVersion = 0;

    $("body").on("click", ".delete-btn", function (e) {
        var key = $(this).attr("data-key");
        xnote.confirm("准备删除【" + key + "】，请确认", function (confirmed) {
            var params = {key: key};
            $.post("?action=delete", params, function (resp) {
                search();
            });
        });
    }); 

    $("body").on("click", ".view-btn", function (e) {
        var value = $(this).attr("data-value");
        var text = $("<textarea>").text(value).addClass("value-detail");
        xnote.showDialog("数据详情", text.prop("outerHTML"));
    }); 

    $(".do-search-btn").click(function (e) {
        search();    
    });

    // 搜索接口
    function search() {
        globalVersion++;
        doSearch("", [], 0, globalVersion);
    }

    // 执行搜索
    function doSearch(cursor, result, scanned, version) {
        if (version != globalVersion) {
            return;
        }
        var maxResultCount = 100;
        var prefix = $("[name=prefix]").val();
        var reverse = $("[name=reverse]").prop("checked");
        var keyword = $("[name=db_key]").val();
        var userName = $("[name=q_user_name]").val();
        var params = {
            action: "search",
            keyword: keyword,
            reverse: reverse,
            cursor: cursor,
            prefix: prefix,
            q_user_name: userName,
        };

        $.get("", params, function (resp) {
            console.log("search result", resp);
            if (resp.code != "success") {
                xnote.alert(resp.message);
            } else {
                scanned += resp.scanned;
                for (var i = 0; i < resp.data.length; i++) {
                    var item = resp.data[i];
                    if (item.value.length>100) {
                        item.valueShort = item.value.substring(0,97) + "...";
                    } else {
                        item.valueShort = item.value;
                    }
                    result.push(item);
                }
                var hasTooManyResult = result.length > maxResultCount;
                if (hasTooManyResult) {
                    result = result.slice(0, maxResultCount);
                }

                var html = $("#result-rows-template").renderTemplate({
                    result: result,
                    scanned: scanned,
                });
                $(".result-rows").html(html);
                if (hasTooManyResult) {
                    xnote.toast("结果过多，只展示前面" + maxResultCount + "条记录");
                    return;
                }

                var hasNext = resp.has_next;
                if (hasNext) {
                    doSearch(resp.next_cursor, result, scanned, version);
                }
            }
        });
    };

    // 初始化
    search();
});
</script>

"""

META_HTML = """
<style>
    .key { width: 75%; }
    .admin-stat-th { width: 25% }
</style>

{% include system/component/db_nav.html %}

<div class="card admin-stat">
    <div class="card-title"> 
        <span>元数据</span>

        <div class="float-right">
            {% if hide_index != "true" %}
                <a class="btn btn-default" href="?p={{p}}&hide_index=true&tab=meta">隐藏索引</a>
            {% else %}
                <a class="btn btn-default" href="?p={{p}}&hide_index=false&tab=meta">展示索引</a>
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
        return dict(code="success")

    @xauth.login_required("admin")
    def do_search(self):
        prefix = xutils.get_argument("prefix", "")
        cursor = xutils.get_argument("cursor", "")
        keyword = xutils.get_argument("keyword", "")
        reverse = xutils.get_argument("reverse", False, type=bool)
        q_user_name = xutils.get_argument("q_user_name", "")
        result = []

        if q_user_name != "":
            prefix = prefix + ":" + q_user_name
        
        if prefix != "" and prefix[-1] != ":":
            prefix += ":"

        limit = 200
        if reverse:
            key_from = None
            key_to = cursor
        else:
            key_from = cursor
            key_to = None

        if key_from == "":
            key_from = None
        if key_to == "":
            key_to = None

        scanned = 0
        next_cursor = ""
        keywords = textutil.split_words(keyword)

        for key, value in dbutil.prefix_iter(
                prefix, key_from=key_from, key_to=key_to, include_key=True, limit=limit+1,
                parse_json=False, reverse=reverse, scan_db=True):
            if scanned < limit and (textutil.contains_all(key, keywords) or textutil.contains_all(value, keywords)):
                item = Storage(key=key, value=value)
                result.append(item)
            scanned += 1
            next_cursor = key

        has_next = False
        if scanned > limit:
            scanned = limit
            has_next = True

        return dict(code="success", data=result, has_next=has_next, next_cursor=next_cursor, scanned=scanned)

    def handle(self, input):
        action = xutils.get_argument("action", "")
        db_key = xutils.get_argument("db_key", "")
        q_user_name = xutils.get_argument("q_user_name", "")
        prefix = xutils.get_argument("prefix", "")
        reverse = xutils.get_argument("reverse", "")
        key_from = xutils.get_argument("key_from", "")

        if action == "delete":
            return self.do_delete()

        if action == "search":
            return self.do_search()

        result = []
        need_reverse = parse_bool(reverse)
        max_scan = 10000
        self.scan_count = 0
        self.error = ""
        self.last_key = ""

        real_prefix = prefix
        if q_user_name != "":
            real_prefix = prefix + ":" + q_user_name

        def func(key, value):
            # print("db_scan:", key, value)
            self.scan_count += 1
            if self.scan_count > max_scan:
                self.error = "too many scan"
                return False

            if not key.startswith(real_prefix):
                return False

            if db_key in value:
                self.last_key = key
                result.append((key, value))
                if len(result) > 30:
                    return False

            return True

        if key_from == "" and real_prefix != "":
            key_from = real_prefix + ":"

        if need_reverse:
            key_to = key_from.encode("utf8") + b'\xff'
            dbutil.scan(key_to=key_to, func=func,
                        reverse=True, parse_json=False)
        else:
            dbutil.scan(key_from=key_from, func=func,
                        reverse=False, parse_json=False)

        kw = Storage()
        kw.result = result
        kw.table_dict = dbutil.get_table_dict_copy()
        kw.prefix = prefix
        kw.db_key = db_key
        kw.reverse = reverse
        kw.get_display_value = get_display_value
        kw.error = self.error
        kw.last_key = self.last_key
        kw.table_names = dbutil.get_table_names()
        kw.q_user_name = q_user_name
        kw.is_reverse = (reverse == "true")

        self.handle_admin_stat_list(kw)

        html = self.get_html()
        self.writetemplate(html, **kw)

    def get_html(self):
        p = xutils.get_argument("p", "")
        if p == "meta":
            return META_HTML
        return SCAN_HTML

    def handle_admin_stat_list(self, kw):
        p = xutils.get_argument("p", "")
        if p != "meta":
            return
        hide_index = xutils.get_argument("hide_index", "true")

        admin_stat_list = []
        if xauth.is_admin():
            table_dict = dbutil.get_table_dict_copy()
            table_values = sorted(table_dict.values(),
                                  key=lambda x: (x.category, x.name))
            for table_info in table_values:
                name = table_info.name
                if hide_index == "true" and name.startswith("_index"):
                    continue
                admin_stat_list.append([table_info.category,
                                        table_info.name,
                                        table_info.description,
                                        dbutil.count_table(name, use_cache=True)])

        kw.admin_stat_list = admin_stat_list


xurls = (
    "/system/db_scan", DbScanHandler,
    "/system/db_admin", DbScanHandler,
    "/system/leveldb_admin", DbScanHandler,
)
