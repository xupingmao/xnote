# encoding=utf-8
# 月历组件(MonthCalendar)示例，对应 /examples/month_calendar
import xutils

from datetime import date
from xutils import Storage
from xnote.plugin.table_plugin import BasePlugin
from xnote.webui import MonthCalendar
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab

BODY_HTML = """
{% include examples/component/example_nav_tab.html %}

<div class="card">
    <span class="card-title">月历: 年份/月份选择 + 指定日期的文字与链接（带标题行）</span>
    {% raw month_calendar.render() %}
</div>

<div class="card">
    <span class="card-title">月历: 不带选择器的静态月历（周日开头，自定义标题）</span>
    {% raw static_calendar.render() %}
</div>

<div class="card">
    <span class="card-title">用法</span>
    <pre class="x-calendar-code">
from xnote.webui import MonthCalendar

calendar = MonthCalendar(year=2026, month=10, base_url="/examples/month_calendar",
                         show_title=True, title="2026年10月 · 假期安排")
# 单个日期: 纯文字
calendar.add_date_text("2026-10-01", "国庆节")
# 日期范围: 10.1 - 10.7 每天都显示
calendar.add_date_text("2026-10-01", "假期", end_date="2026-10-07")
# 链接 + hover 提示
calendar.add_date_link("2026-10-06", "/note/view?name=plan", "月度计划", tip="点击查看月度计划")

# 模板里用 raw 表达式输出: {{'{%'}} raw calendar.render() %}
self.writehtml(HTML, calendar=calendar)
    </pre>
</div>
"""


def build_month_calendar():
    """带年月选择的月历：年份/月份从查询参数读取，切换时跳回本页"""
    year = xutils.get_argument_int("year", 0)
    month = xutils.get_argument_int("month", 0)
    calendar = MonthCalendar(year=year, month=month, base_url="/examples/month_calendar",
                             show_title=True)

    # 标题单独一行，缺省文字是「YYYY年M月」，也可以传 title 自定义
    year = calendar.year
    month = calendar.month

    def date_str(day: int) -> str:
        return "%s-%02d-%02d" % (year, month, day)

    # 日期范围: 1号到5号每天都显示「月初」
    calendar.add_date_text(date_str(1), "月初", end_date=date_str(5), tip="本月头几天")
    # 单个日期: 链接
    calendar.add_date_link(date_str(6), "/note/view?name=plan", "月度计划", tip="点击查看月度计划")
    calendar.add_date_link(date_str(15), "/note/view?name=review", "月中复盘")
    # 日期范围: 20号到22号
    calendar.add_date_link(date_str(20), "/examples/month_calendar", "里程碑",
                           end_date=date_str(22), tip="里程碑节点")
    calendar.add_date_text(calendar.today.strftime("%Y-%m-%d"), "今天")
    return calendar


def build_static_calendar():
    """不带选择器的静态月历（周日开头，自定义标题）"""
    today = date.today()
    calendar = MonthCalendar(year=today.year, month=today.month, week_start=6,
                             show_title=True, title="静态月历（周日开头）")
    calendar.add_date_text("%s-%02d-01" % (today.year, today.month), "月初")
    return calendar


class MonthCalendarExampleHandler(BasePlugin):
    title = "月历组件"
    rows = 0
    parent_link = LinkConfig.develop_index

    def handle(self, input=""):
        kw = Storage()
        kw.example_tab = get_example_tab(tab_default="month_calendar")
        kw.month_calendar = build_month_calendar()
        kw.static_calendar = build_static_calendar()
        self.writehtml(BODY_HTML, **kw)


xurls = (
    r"/examples/month_calendar", MonthCalendarExampleHandler,
)
