# encoding=utf-8
# 日历组件示例 tab，对应 /examples/example/calendar
import xutils

from datetime import date
from xutils import Storage
from xnote.core import xauth
from xnote.plugin.table_plugin import BaseTablePlugin, BasePlugin
from xnote.webui.calendar import ContributionCalendar
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab


class CalendarExampleHandler(BasePlugin):
    title = "日历组件"
    rows = 0
    parent_link = LinkConfig.develop_index

    HTML = """
{% include examples/component/example_nav_tab.html %}

<h3 class="card-title">贡献日历</h3>
<div class="card">
    {% raw calendar.render() %}
</div>

<h3 class="card-title">日期选择器</h3>
<div class="card">
    <div class="row">
        <div class="input-group">
            <label>年份选择器</label>
            <input type="text" class="date" data-date-type="year">
        </div>
        <div class="input-group">
            <label>月份选择器</label>
            <input type="text" class="date" data-date-type="month">
        </div>
    </div>

    <div class="row">
        <div class="input-group">
            <label>日期选择器</label>
            <input type="text" class="date" data-date-type="date">
        </div>
        <div class="input-group">
            <label>时间选择器</label>
            <input type="text" class="date" data-date-type="time">
        </div>
        <div class="input-group">
            <label>日期时间选择器</label>
            <input type="text" class="date" data-date-type="datetime">
        </div>
    </div>
</div>

{% include common/script/load_laydate.html %}
"""

    def handle(self, input=""):
        start = date(2020, 1, 1)
        end = date(2020, 12, 31)
        data = {
            "2020-01-01": 5,
            "2020-02-16": 1,
            "2020-03-11": 10,
            "2020-04-01": 20,
        }
        calendar = ContributionCalendar(start_date=start, end_date=end, data = data)
        kw = Storage()
        kw.example_tab = get_example_tab()
        kw.calendar = calendar
        self.writehtml(self.HTML, **kw)


xurls = (
    r"/examples/example/calendar", CalendarExampleHandler,
)
