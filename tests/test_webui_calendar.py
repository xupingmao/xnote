# -*- coding: utf-8 -*-
"""月历组件(MonthCalendar)的构建与渲染测试"""
from datetime import date

from . import test_base
from xnote.webui import MonthCalendar

app = test_base.init()
BaseTestCase = test_base.BaseTestCase


def _to_str(html):
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return html


class TestMonthCalendarBuild(BaseTestCase):

    def test_default_use_today(self):
        """不传年月时取当前日期"""
        today = date.today()
        calendar = MonthCalendar()
        self.assertEqual(calendar.year, today.year)
        self.assertEqual(calendar.month, today.month)

    def test_weeks_are_6x7(self):
        """固定渲染 6 行 7 列，不同月份高度一致"""
        calendar = MonthCalendar(year=2026, month=10)
        self.assertEqual(len(calendar.weeks), 6)
        for week in calendar.weeks:
            self.assertEqual(len(week), 7)

    def test_first_cell_and_month_start(self):
        """2026-10-01 是周四，周一开始 => 第 4 个格子(下标3)，前面补 9 月"""
        calendar = MonthCalendar(year=2026, month=10)
        first_week = calendar.weeks[0]
        self.assertEqual(first_week[0].date_str, "2026-09-28")
        self.assertFalse(first_week[0].in_month)

        month_start = first_week[3]
        self.assertEqual(month_start.date_str, "2026-10-01")
        self.assertTrue(month_start.in_month)
        self.assertEqual(month_start.day, 1)

    def test_out_month_days_are_filled(self):
        """末尾补齐下个月的日期"""
        calendar = MonthCalendar(year=2026, month=10)
        last_cell = calendar.weeks[-1][-1]
        self.assertEqual(last_cell.date_str, "2026-11-08")
        self.assertFalse(last_cell.in_month)

    def test_today_flag(self):
        """今天的单元格有标记"""
        calendar = MonthCalendar()
        today_cells = [cell for week in calendar.weeks for cell in week if cell.is_today]
        self.assertEqual(len(today_cells), 1)
        self.assertEqual(today_cells[0].date_str, date.today().strftime("%Y-%m-%d"))

    def test_week_start_sunday(self):
        """week_start=6 时周日开头"""
        calendar = MonthCalendar(year=2026, month=10, week_start=6)
        self.assertEqual(calendar.week_labels[0], "日")
        # 2026-10-01 是周四 => 周日开头的第 5 个格子(下标4)
        self.assertEqual(calendar.weeks[0][4].date_str, "2026-10-01")


class TestMonthCalendarDateInfo(BaseTestCase):

    def test_add_date_text(self):
        """纯文字：渲染成 span，没有链接"""
        calendar = MonthCalendar(year=2026, month=10)
        infos = calendar.add_date_text("2026-10-01", "国庆节", tip="放假")
        self.assertEqual(len(infos), 1)
        html = _to_str(calendar.render())
        self.assertIn('<span class="x-calendar-info " title="放假">国庆节</span>', html)
        self.assertIn('data-tip="放假"', html)

    def test_add_date_link(self):
        """链接：渲染成 a 标签"""
        calendar = MonthCalendar(year=2026, month=10)
        calendar.add_date_link("2026-10-06", "/note/view?name=plan", "月度计划")
        html = _to_str(calendar.render())
        self.assertIn('<a class="x-calendar-info " href="/note/view?name=plan">月度计划</a>', html)

    def test_add_date_text_with_range(self):
        """日期范围：10.01 - 10.07 每天都显示"""
        calendar = MonthCalendar(year=2026, month=10)
        infos = calendar.add_date_text("2026-10-01", "假期", end_date="2026-10-07")
        self.assertEqual(len(infos), 7)
        for day in range(1, 8):
            self.assertEqual(len(calendar.get_date_infos("2026-10-%02d" % day)), 1)
        self.assertEqual(len(calendar.get_date_infos("2026-10-08")), 0)
        self.assertEqual(_to_str(calendar.render()).count(">假期</span>"), 7)

    def test_add_date_link_with_range(self):
        """日期范围 + 链接：支持 date 对象，起止写反也会自动纠正"""
        calendar = MonthCalendar(year=2026, month=10)
        infos = calendar.add_date_link(date(2026, 10, 22), "/note/plan", "冲刺",
                                       end_date=date(2026, 10, 20))
        self.assertEqual(len(infos), 3)
        for day in (20, 21, 22):
            day_infos = calendar.get_date_infos("2026-10-%02d" % day)
            self.assertEqual(len(day_infos), 1)
            self.assertEqual(day_infos[0].href, "/note/plan")

    def test_remove_range(self):
        """按范围清除"""
        calendar = MonthCalendar(year=2026, month=10)
        calendar.add_date_text("2026-10-01", "假期", end_date="2026-10-03")
        calendar.remove_date_infos("2026-10-01", end_date="2026-10-03")
        for day in (1, 2, 3):
            self.assertEqual(calendar.get_date_infos("2026-10-%02d" % day), [])
        self.assertNotIn("假期", _to_str(calendar.render()))

    def test_add_date_info_accepts_date_object(self):
        """日期参数支持 date 对象"""
        calendar = MonthCalendar(year=2026, month=10)
        calendar.add_date_info(date(2026, 10, 8), text="提醒", href="/todo/task")
        infos = calendar.get_date_infos("2026-10-08")
        self.assertEqual(len(infos), 1)
        self.assertEqual(infos[0].href, "/todo/task")
        self.assertIn('data-date="2026-10-08"', _to_str(calendar.render()))

    def test_multiple_infos_on_one_day(self):
        """同一天可以挂多条信息"""
        calendar = MonthCalendar(year=2026, month=10)
        calendar.add_date_info("2026-10-20", text="A")
        calendar.add_date_info("2026-10-20", text="B", href="/link")
        self.assertEqual(len(calendar.get_date_infos("2026-10-20")), 2)
        html = _to_str(calendar.render())
        self.assertIn(">A</span>", html)
        self.assertIn('href="/link">B</a>', html)

    def test_remove_date_infos(self):
        """清除某天的信息"""
        calendar = MonthCalendar(year=2026, month=10)
        calendar.add_date_text("2026-10-01", "国庆节")
        self.assertEqual(len(calendar.get_date_infos("2026-10-01")), 1)
        calendar.remove_date_infos("2026-10-01")
        self.assertEqual(len(calendar.get_date_infos("2026-10-01")), 0)
        self.assertNotIn("国庆节", _to_str(calendar.render()))

    def test_get_date_infos_empty(self):
        """没有信息的日期返回空列表"""
        calendar = MonthCalendar(year=2026, month=10)
        self.assertEqual(calendar.get_date_infos("2026-10-02"), [])


class TestMonthCalendarRender(BaseTestCase):

    def test_cells_are_square(self):
        """单元格渲染成 x-calendar-cell，宽高由 CSS aspect-ratio 保证一致"""
        calendar = MonthCalendar(year=2026, month=10)
        html = _to_str(calendar.render())
        self.assertEqual(html.count("x-calendar-cell"), 42)
        self.assertIn("x-calendar-grid", html)

    def test_hover_tip_class(self):
        """有 tip 的单元格带 has-tip 标记（hover 气泡由 CSS 实现）"""
        calendar = MonthCalendar(year=2026, month=10)
        calendar.add_date_text("2026-10-01", "国庆节", tip="放假")
        html = _to_str(calendar.render())
        self.assertIn("x-calendar-has-tip", html)

    def test_year_month_selector(self):
        """有 base_url 时渲染年份/月份下拉 + 上个月/下个月/今天"""
        calendar = MonthCalendar(year=2026, month=10, base_url="/examples/month_calendar")
        html = _to_str(calendar.render())
        self.assertIn('<select class="x-calendar-year" name="year"', html)
        self.assertIn('<select class="x-calendar-month" name="month"', html)
        self.assertIn('href="/examples/month_calendar?year=2026&amp;month=9"', html)
        self.assertIn('href="/examples/month_calendar?year=2026&amp;month=11"', html)
        self.assertIn("x-calendar-today", html)
        self.assertIn('<option value="2026" selected>', html)
        self.assertIn('<option value="10" selected>', html)

    def test_head_is_one_row(self):
        """上/下月 + 年月下拉 + 今天在同一个 x-calendar-head 容器内"""
        calendar = MonthCalendar(year=2026, month=10, base_url="/x")
        html = _to_str(calendar.render())
        head_start = html.index('class="x-calendar-head"')
        head_end = html.index("</div>", head_start)
        head = html[head_start:head_end]
        for part in ("x-calendar-prev", "x-calendar-year", "x-calendar-month",
                     "x-calendar-next", "x-calendar-today"):
            self.assertIn(part, head)

    def test_no_selector_without_base_url(self):
        """没有 base_url 时不出现下拉，也不渲染 head"""
        calendar = MonthCalendar(year=2026, month=10)
        html = _to_str(calendar.render())
        self.assertNotIn("x-calendar-year", html)
        self.assertNotIn("x-calendar-head", html)

    def test_title_is_optional(self):
        """标题默认不显示，show_title=True 时单独一行"""
        default_cal = MonthCalendar(year=2026, month=10)
        self.assertNotIn("x-calendar-title", _to_str(default_cal.render()))

        title_cal = MonthCalendar(year=2026, month=10, show_title=True)
        html = _to_str(title_cal.render())
        self.assertIn('<div class="x-calendar-title">2026年10月</div>', html)

    def test_custom_title(self):
        """title 参数可以自定义标题文字"""
        calendar = MonthCalendar(year=2026, month=10, show_title=True,
                                 title="2026年10月 · 假期安排")
        self.assertEqual(calendar.title, "2026年10月 · 假期安排")
        self.assertIn("2026年10月 · 假期安排", _to_str(calendar.render()))

    def test_extra_params_are_kept(self):
        """跳转地址保留额外查询参数"""
        calendar = MonthCalendar(year=2026, month=1, base_url="/todo/task",
                                 params={"project_id": "1"})
        self.assertEqual(calendar.prev_url, "/todo/task?project_id=1&year=2025&month=12")
        self.assertEqual(calendar.next_url, "/todo/task?project_id=1&year=2026&month=2")
        html = _to_str(calendar.render())
        self.assertIn('<input type="hidden" name="project_id" value="1">', html)

    def test_year_range(self):
        """年份下拉向前后扩展"""
        calendar = MonthCalendar(year=2026, month=10, base_url="/x", year_range=2)
        self.assertEqual(calendar.year_options, [2024, 2025, 2026, 2027, 2028])

    def test_today_url(self):
        """今天按钮指向当前年月"""
        calendar = MonthCalendar(year=2020, month=1, base_url="/x")
        today = date.today()
        self.assertEqual(calendar.today_url, "/x?year=%s&month=%s" % (today.year, today.month))

    def test_week_labels(self):
        """默认周一开头"""
        calendar = MonthCalendar(year=2026, month=10)
        self.assertEqual(calendar.week_labels, ["一", "二", "三", "四", "五", "六", "日"])
        html = _to_str(calendar.render())
        self.assertIn('<div class="x-calendar-week-cell">一</div>', html)
