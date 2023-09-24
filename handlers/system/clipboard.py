# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/07/18 22:55:08
# @modified 2019/07/20 22:42:44
import xutils
import xmanager
import logging

from xtemplate import BasePlugin
from xutils import dateutil
from xutils import dbutil

HTML = """
<!-- Html -->
<style>
.th-time {
    with: 30%;
}
.th-content {
    width: 60%;
}
.th-op {
    width: 10%;
}
.value-detail {
    position: absolute;
    width:100%;
    top: 0px;
    bottom: 30px;
    overflow-y: auto;
}
</style>

{% include system/component/system_log_tab.html %}

<div class="card">
    {% if len(records) == 0 %}
        {% include common/text/empty_text.html %}
    {% else %}
        <table class="table">
            <tr>
                <th class="th-time">时间</th>
                <th class="th-content">内容</th>
                <th class="th-op">操作</th>
            </tr>
        {% for r in records %}
            <tr>
                <td>{{r.create_time}}</td>
                <td>{{r.content}}</td>
                <td><button data-id="{{r._id}}" onclick="xnoteOpenClipDetail(this)" class="btn btn-default">查看</button></td>
            </tr>
        {% end %}
        </table>
    {% end %}
</div>

<div class="card">
    {% include common/pagination.html %}
</div>

<script>
function xnoteOpenClipDetail(target) {
    var id = $(target).attr("data-id");
    var params = {};
    params.id = id;

    $.get("?op=detail", params, function (resp) {
        var value = resp.data;
        var content = "";
        if (value) {
            content = value.content;
        }
        var text = $("<textarea>").text(content).addClass("value-detail");
        xnote.showDialog("数据详情", text.prop("outerHTML"), ["确定"]);
    });
};
</script>
"""

ASIDE_HTML = """
{% include system/component/admin_nav.html %}
"""


dbutil.register_table("clip_log", "剪切板历史")

class ClipLogDO(xutils.Storage):

    def __init__(self):
        self.create_time = ""
        self.content = ""

class ClipLogDao:

    db = dbutil.get_table("clip_log")
    last_log_content = ""
    max_log_count = 500
    max_content_size = 1024 * 1024 # 1MB

    @classmethod
    def init(cls):
        last = cls.db.get_last()
        if last != None:
            cls.last_log_content = last.content

    @classmethod
    def add_log(cls, log_content=""):
        log_content = log_content.strip()
        if log_content == "":
            return
        if log_content == cls.last_log_content:
            return
        
        if len(log_content) > cls.max_content_size:
            logging.warn("clipboard data too large")
            log_content = log_content[:cls.max_content_size]
        
        record = ClipLogDO()
        record.create_time = dateutil.format_datetime()
        record.content = log_content
        cls.db.insert(record)
        cls.last_log_content = log_content
        cls.clear_old_logs()
    
    @classmethod
    def clear_old_logs(cls):
        buf_size = 10
        if cls.db.count() > cls.max_log_count + buf_size:
            for record in cls.db.list(limit=buf_size):
                cls.db.delete(record)

    @classmethod
    def list_recent(cls, offset=0, limit=100):
        return cls.db.list(reverse=True, limit=limit)
    
    @classmethod
    def get_by_id(cls, id=""):
        return cls.db.get_by_id(id)
    
    @classmethod
    def count(cls):
        return cls.db.count()


ClipLogDao.init()

class Main(BasePlugin):

    title = "剪切板记录"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = "system"

    editable = False
    show_aside = True
    

    def handle(self, input):
        # 输入框的行数
        watch_clipboard()
        self.rows = 0
        self.btn_text = '添加'
        op = xutils.get_argument_str("op")
        page = xutils.get_argument_int("page", 1)
        page_size = 20
        offset = (page-1) * page_size

        if op == "detail":
            return self.handle_detail()

        kw = xutils.Storage()
        kw.page = page
        kw.page_size = page_size
        kw.page_total = ClipLogDao.count()
        kw.records = ClipLogDao.list_recent(offset=offset, limit=page_size)
        self.writehtml(HTML, **kw)
        self.write_aside(ASIDE_HTML)

    def handle_detail(self):
        id = xutils.get_argument_str("id")
        return dict(
            code = "success",
            data = ClipLogDao.get_by_id(id)
        )

    def on_init(self, context=None):
        # 插件初始化操作
        pass

@xmanager.listen("cron.minute")
def watch_clipboard(ctx=None):
    try:
        import pyperclip
        content = pyperclip.paste()
        ClipLogDao.add_log(content)
    except:
        pass


xurls = (
    r"/system/clipboard-monitor", Main
)