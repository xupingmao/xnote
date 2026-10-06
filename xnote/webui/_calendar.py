from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import urlencode

from xnote.core import xtemplate
from datetime import date, datetime, timedelta
from xutils import textutil
from xnote.webui.base import BaseComponent

class CalendarItem:
    def __init__(self, date: date, count = 0):
        self.date = date
        self.count = count
        self.css_class = self.calc_css_class(count)
        if count == 0:
            self.tip = f"{self.date} 无事发生"
        else:
            self.tip = f"{self.date} 发生了{count}个事件"


    def calc_css_class(self, count=0):
        if count == 0:
            return "contribution-0"
        if count <= 3:
            return "contribution-1"
        if count <= 7:
            return "contribution-2"
        if count <= 14:
            return "contribution-3"
        return "contribution-4"

class CalendarRow:
    def __init__(self, label: str):
        self.label = label
        self.items: List[CalendarItem] = []

class MonthInfo:
    def __init__(self, label="", month = 1, cols = 1):
        self.label = label
        self.month = month
        self.cols = cols

class MonthList:
    def __init__(self):
        self.items: List[MonthInfo] = []

    def add_month(self, month = 0):
        if len(self.items) == 0:
            self.items.append(MonthInfo(label=f"{month}月", month=month, cols=1))
        elif self.items[-1].month != month:
            self.items.append(MonthInfo(label=f"{month}月", month=month, cols=1))
        else:
            self.items[-1].cols += 1

    def handle_rows(self, rows: List[CalendarRow]):
        # 以每周的最后一天的月份为准
        for cell in rows[6].items:
            self.add_month(cell.date.month)


class ContributionStats:
    pass

class ContributionCalendar(BaseComponent):

    show_stats = False
    stats = ContributionStats()

    def __init__(self, start_date = date(2020, 1, 1), end_date = date(2020, 12, 31),
                 data: Dict[str, int] = {}):
        self.id = textutil.create_uuid()
        self.rows: List[CalendarRow] = []
        month_list = MonthList()

        start_date = self.resolve_start_date(start_date)
        end_date = self.resolve_end_date(end_date)

        labels = ["一", "二", "三", "四", "五", "六", "日"]
        rows = [CalendarRow(label=x) for x in labels]
        date = start_date
        max_count = 1000
        count = 0
        while date <= end_date and count < max_count:
            row = rows[date.weekday()]
            count = data.get(str(date), 0)
            row.items.append(CalendarItem(date=date, count=count))
            date = date + timedelta(days=1)
            count += 1
        
        month_list.handle_rows(rows)
        self.rows = rows
        self.month_list = month_list.items

        # 星期占1列, 一个月最多占5列, 最后一个月可能不完整
        cols = len(rows[0].items) + 6
        width = cols * 12 + 1
        self.row_style = f"min-width: {width}px"


    def resolve_end_date(self, date: date) -> date:
        if date.weekday == 6:
            return date
        diff = 6 - date.weekday()
        return date + timedelta(days=diff)
    
    def resolve_start_date(self, date: date) -> date:
        if date.weekday == 0:
            return date
        return date - timedelta(days = date.weekday())

    def render(self):
        return xtemplate.render("common/date/contribution_calendar.html", calendar = self)


# 日期参数的几种写法: YYYY-MM-DD 字符串 / date / datetime
DateValue = Union[str, date, datetime]


def format_date_str(value: date) -> str:
    """date -> YYYY-MM-DD"""
    # isoformat 比 strftime 快不少，批量构建时能省下可观的开销
    return value.isoformat()


# 日期字符串缓存，批量构建时同一个日期会被反复解析
_DATE_KEY_CACHE: Dict[Union[str, date], str] = {}
_DATE_KEY_CACHE_MAX = 10000


def format_date_key(value: DateValue) -> str:
    """date/datetime/字符串 -> YYYY-MM-DD（带缓存）"""
    cacheable = isinstance(value, str) or isinstance(value, date)
    if cacheable:
        key = _DATE_KEY_CACHE.get(value)
        if key is not None:
            return key

    key = format_date_str(MonthCalendar.parse_date(value))
    if cacheable and len(_DATE_KEY_CACHE) < _DATE_KEY_CACHE_MAX:
        _DATE_KEY_CACHE[value] = key
    return key


class CalendarDateInfo:
    """某个日期上要展示的一条信息（文字或链接）"""

    def __init__(self, date_str: str = "", text: str = "", href: str = "",
                 tip: str = "", css_class: str = ""):
        self.date_str = date_str
        self.text = text
        self.href = href
        self.tip = tip
        self.css_class = css_class


class CalendarCell:
    """月历里的一个单元格"""

    def __init__(self, day: int = 0, cur_date: Optional[date] = None, in_month: bool = True):
        self.day = day
        self.date: Optional[date] = cur_date
        self.date_str = format_date_str(cur_date) if cur_date else ""
        self.in_month = in_month
        self.is_today = False
        self.infos: List[CalendarDateInfo] = []

    def add_info(self, info: CalendarDateInfo) -> "CalendarCell":
        self.infos.append(info)
        return self

    @property
    def tip(self) -> str:
        """hover 提示，取第一条带 tip 的信息"""
        for info in self.infos:
            if info.tip:
                return info.tip
        return ""


# add_date_infos 支持的单条数据类型: dict / CalendarDateInfo / (date, text[, href])
CalendarDateItem = Union[Dict[str, Any], CalendarDateInfo, tuple, list]


class MonthCalendar(BaseComponent):
    """月历组件

    - 支持切换年份/月份：【上个月】+ 年份/月份下拉 + 【下个月】+【今天】在同一行，
      标题单独一行且可选（show_title=True 打开，title 可自定义文字）
    - 支持在指定日期（或日期范围）上挂文字或链接，比如:

        calendar = MonthCalendar(year=2026, month=10, base_url="/examples/month_calendar")
        calendar.add_date_text("2026-10-01", "国庆节")
        calendar.add_date_text("2026-10-01", "假期", end_date="2026-10-07")   # 覆盖一整段
        calendar.add_date_link("2026-10-06", "/note/view?name=plan", "月度计划", tip="点击查看")

    批量添加用 add_date_infos（一次调用写完，只做增量更新，不重建网格）:

        calendar.add_date_infos([
            {"date": "2026-10-01", "text": "国庆节"},
            {"date": "2026-10-06", "text": "月度计划", "href": "/note/view?name=plan"},
            {"date": "2026-10-20", "text": "冲刺", "end_date": "2026-10-22"},
        ])

    - 单元格是等宽等高的正方形（CSS aspect-ratio），hover 有高亮 + 提示气泡

    year/month 缺省取当前日期。切换年月时会跳转到 base_url（带上 params 里
    的其它查询参数），由页面自己读取 year/month 重新渲染。
    """

    _code = xtemplate.compile_template("""<div class="x-calendar {{calendar.css_class}}" id="{{calendar.id}}">
    {% if calendar.base_url %}
    <div class="x-calendar-head">
        <a class="btn btn-default x-calendar-prev" title="上个月" href="{{calendar.prev_url}}">&lt;</a>
        <form class="x-calendar-form" method="get" action="{{calendar.base_url}}">
            {% for key, value in calendar.param_items %}
            <input type="hidden" name="{{key}}" value="{{value}}">
            {% end %}
            <select class="x-calendar-year" name="year" onchange="this.form.submit()">
                {% for item in calendar.year_options %}
                <option value="{{item}}" {% if item == calendar.year %}selected{% end %}>{{item}}年</option>
                {% end %}
            </select>
            <select class="x-calendar-month" name="month" onchange="this.form.submit()">
                {% for item in calendar.month_options %}
                <option value="{{item}}" {% if item == calendar.month %}selected{% end %}>{{item}}月</option>
                {% end %}
            </select>
        </form>
        <a class="btn btn-default x-calendar-next" title="下个月" href="{{calendar.next_url}}">&gt;</a>
        <a class="btn btn-default x-calendar-today" href="{{calendar.today_url}}">今天</a>
    </div>
    {% end %}

    {% if calendar.show_title %}
    <div class="x-calendar-title">{{calendar.title}}</div>
    {% end %}

    <div class="x-calendar-week">
        {% for label in calendar.week_labels %}
        <div class="x-calendar-week-cell">{{label}}</div>
        {% end %}
    </div>

    <div class="x-calendar-grid">
        {% for week in calendar.weeks %}
            {% for cell in week %}
            <div class="x-calendar-cell{% if not cell.in_month %} x-calendar-out{% end %}{% if cell.is_today %} x-calendar-today-cell{% end %}{% if cell.infos %} x-calendar-has-info{% end %}{% if cell.tip %} x-calendar-has-tip{% end %}" data-date="{{cell.date_str}}" data-tip="{{cell.tip}}">
                <div class="x-calendar-day">{{cell.day}}</div>
                <div class="x-calendar-infos">
                    {% for info in cell.infos %}
                        {% if info.href %}
                        <a class="x-calendar-info {{info.css_class}}" href="{{info.href}}"{% if info.tip %} title="{{info.tip}}"{% end %}>{{info.text}}</a>
                        {% else %}
                        <span class="x-calendar-info {{info.css_class}}"{% if info.tip %} title="{{info.tip}}"{% end %}>{{info.text}}</span>
                        {% end %}
                    {% end %}
                </div>
            </div>
            {% end %}
        {% end %}
    </div>
</div>
""", name="xnote.webui.month_calendar")

    def __init__(self, year: int = 0, month: int = 0, base_url: str = "",
                 params: Optional[Dict[str, Any]] = None,
                 year_range: int = 5, week_start: int = 0, css_class: str = "",
                 title: str = "", show_title: bool = False):
        """
        :param year: 年份，缺省取当前年
        :param month: 月份(1-12)，缺省取当前月
        :param base_url: 切换年月时跳转的地址，为空时只渲染静态月历（不显示选择器）
        :param params: 跳转时额外带上的查询参数
        :param year_range: 年份下拉框向前后扩展的年数
        :param week_start: 每周的第一天，0=周一, 6=周日
        :param title: 标题文字，缺省用「YYYY年M月」
        :param show_title: 是否显示标题行（标题单独一行，与年月选择器分开）
        """
        self.id = "calendar-" + textutil.create_uuid()
        self.css_class = css_class
        self.base_url = base_url
        self.params: Dict[str, Any] = params if params else {}
        self.year_range = year_range
        self.week_start = week_start
        self.show_title = show_title
        self._title = title

        today = date.today()
        self.year = year if year else today.year
        self.month = month if month else today.month
        self.today = today

        # date_str -> 该日期上的信息列表
        self.date_infos: Dict[str, List[CalendarDateInfo]] = {}
        # date_str -> CalendarCell, 加/删信息时按日期直接定位单元格，避免重建整个网格
        self._cell_index: Dict[str, CalendarCell] = {}
        # 网格缓存，None 时由 weeks 属性触发构建
        self._weeks: Optional[List[List[CalendarCell]]] = None
        self.build_weeks()

    # ---------- 对外接口: 在指定日期上设置链接/文字 ----------

    def add_date_info(self, date_str: DateValue, text: str = "", href: str = "",
                      tip: str = "", css_class: str = "") -> CalendarDateInfo:
        """在【单个】日期上添加一条信息（有 href 渲染成链接，否则渲染成文字）

        只做增量更新（不重建网格），可以放心在循环里调用。
        要覆盖一段日期范围请用 add_date_text / add_date_link 的 end_date 参数。
        :param date_str: YYYY-MM-DD 字符串或 date 对象
        """
        return self._append_info(self.format_key(date_str), text, href, tip, css_class)

    def add_date_text(self, date_str: DateValue, text: str = "", tip: str = "",
                      css_class: str = "", end_date: DateValue = "") -> List[CalendarDateInfo]:
        """在指定日期上显示纯文字

        :param date_str: 起始日期，YYYY-MM-DD 字符串或 date 对象
        :param end_date: 结束日期（可选），非空时在 [date_str, end_date] 的每一天都添加
        :return: 添加的 CalendarDateInfo 列表
        """
        return self._add_range(date_str, end_date, text=text, href="", tip=tip, css_class=css_class)

    def add_date_link(self, date_str: DateValue, href: str = "", text: str = "",
                      tip: str = "", css_class: str = "",
                      end_date: DateValue = "") -> List[CalendarDateInfo]:
        """在指定日期上显示一个链接

        :param date_str: 起始日期，YYYY-MM-DD 字符串或 date 对象
        :param end_date: 结束日期（可选），非空时在 [date_str, end_date] 的每一天都添加
        :return: 添加的 CalendarDateInfo 列表
        """
        return self._add_range(date_str, end_date, text=text, href=href, tip=tip, css_class=css_class)

    def add_text_list(self, dates: Sequence[DateValue], text: str = "", tip: str = "",
                      css_class: str = "") -> List[CalendarDateInfo]:
        """在一批（可以不连续的）日期上添加同一段文字

        :param dates: 日期列表，元素是 YYYY-MM-DD 字符串或 date 对象
        :return: 添加的 CalendarDateInfo 列表
        """
        infos: List[CalendarDateInfo] = []
        for item in dates:
            infos.append(self._append_info(self.format_key(item), text, "", tip, css_class))
        return infos

    def add_link_list(self, dates: Sequence[DateValue], href: str = "", text: str = "",
                      tip: str = "", css_class: str = "") -> List[CalendarDateInfo]:
        """在一批（可以不连续的）日期上添加同一个链接

        :param dates: 日期列表，元素是 YYYY-MM-DD 字符串或 date 对象
        :return: 添加的 CalendarDateInfo 列表
        """
        infos: List[CalendarDateInfo] = []
        for item in dates:
            infos.append(self._append_info(self.format_key(item), text, href, tip, css_class))
        return infos

    def add_date_infos(self, items: Sequence[CalendarDateItem], default_text: str = "",
                       default_href: str = "", default_tip: str = "",
                       default_css_class: str = "") -> List[CalendarDateInfo]:
        """批量添加日期信息：一次调用写完所有数据，全程增量更新（不重建网格）

        items 里每一条支持下面几种写法:

            {"date": "2026-10-01", "text": "国庆节"}
            {"date": "2026-10-06", "text": "月度计划", "href": "/note/view?name=plan"}
            {"date": "2026-10-20", "text": "冲刺", "end_date": "2026-10-22"}  # 一段范围
            CalendarDateInfo(date_str="2026-10-08", text="提醒")
            ("2026-10-08", "提醒") / ("2026-10-08", "提醒", "/todo/task")

        dict 的日期键也可以写 date_str / start_date；带 end_date 时覆盖整段范围。

        :param default_xxx: 各字段的缺省值，item 里没写时用它兜底
        :return: 添加的 CalendarDateInfo 列表
        """
        infos: List[CalendarDateInfo] = []
        for item in items:
            infos.extend(self._add_one_item(item, default_text, default_href,
                                            default_tip, default_css_class))
        return infos

    def _add_one_item(self, item: CalendarDateItem, default_text: str = "",
                      default_href: str = "", default_tip: str = "",
                      default_css_class: str = "") -> List[CalendarDateInfo]:
        """解析批量数据里的一条并写入"""
        if isinstance(item, CalendarDateInfo):
            return [self._append_info(self.format_key(item.date_str),
                                      item.text or default_text,
                                      item.href or default_href,
                                      item.tip or default_tip,
                                      item.css_class or default_css_class)]

        if isinstance(item, dict):
            date_str = item.get("date")
            if not date_str:
                date_str = item.get("date_str") or item.get("start_date")
                if not date_str:
                    raise ValueError("add_date_infos: 缺少日期字段 %s" % item)

            end_date = item.get("end_date")
            if end_date:
                return self.add_range_info(
                    date_str, end_date,
                    text=item.get("text") or default_text,
                    href=item.get("href") or default_href,
                    tip=item.get("tip") or default_tip,
                    css_class=item.get("css_class") or default_css_class)

            return [self._append_info(format_date_key(date_str),
                                      item.get("text") or default_text,
                                      item.get("href") or default_href,
                                      item.get("tip") or default_tip,
                                      item.get("css_class") or default_css_class)]

        if isinstance(item, (tuple, list)):
            values = list(item)
            while len(values) < 3:
                values.append("")
            return [self._append_info(self.format_key(values[0]),
                                      values[1] or default_text,
                                      values[2] or default_href,
                                      default_tip, default_css_class)]

        raise ValueError("add_date_infos: 不支持的数据类型 %s" % type(item))

    def add_range_info(self, start_date: DateValue, end_date: DateValue, text: str = "",
                       href: str = "", tip: str = "",
                       css_class: str = "") -> List[CalendarDateInfo]:
        """在一段日期范围内的每一天添加同一条信息（同样只做增量更新）"""
        infos: List[CalendarDateInfo] = []
        for key in self.resolve_date_keys(start_date, end_date):
            infos.append(self._append_info(key, text, href, tip, css_class))
        return infos

    def _add_range(self, date_str: DateValue, end_date: DateValue, text: str = "",
                   href: str = "", tip: str = "",
                   css_class: str = "") -> List[CalendarDateInfo]:
        if end_date:
            return self.add_range_info(date_str, end_date, text=text, href=href,
                                       tip=tip, css_class=css_class)
        return [self.add_date_info(date_str, text=text, href=href, tip=tip, css_class=css_class)]

    def _append_info(self, key: str, text: str = "", href: str = "", tip: str = "",
                     css_class: str = "") -> CalendarDateInfo:
        """写入一条信息

        增量更新：单元格和 date_infos 共用同一个 list，追加一次即可，
        不需要重建整个 6x7 网格（原来每加一条都要重建 42 个单元格）。
        """
        info = CalendarDateInfo(date_str=key, text=text, href=href, tip=tip, css_class=css_class)
        infos = self.date_infos.get(key)
        if infos is None:
            infos = []
            self.date_infos[key] = infos
            cell = self._cell_index.get(key)
            if cell is not None:
                cell.infos = infos
        infos.append(info)
        return info

    def get_date_infos(self, date_str: DateValue) -> List[CalendarDateInfo]:
        """查询某个日期上的信息列表"""
        return self.date_infos.get(self.format_key(date_str), [])

    def get_cell(self, date_str: DateValue) -> Optional[CalendarCell]:
        """取某个日期对应的单元格，不在当前月历显示范围内时返回 None"""
        if self._weeks is None:
            self.build_weeks()
        return self._cell_index.get(self.format_key(date_str))

    def remove_date_infos(self, date_str: DateValue, end_date: DateValue = "") -> None:
        """清除某个日期（或一段日期范围）上的信息（增量更新）"""
        for key in self.resolve_date_keys(date_str, end_date):
            self.date_infos.pop(key, None)
            cell = self._cell_index.get(key)
            if cell is not None:
                cell.infos = []

    def clear_date_infos(self) -> None:
        """清空所有日期上的信息"""
        self.date_infos.clear()
        if self._weeks is None:
            return
        for cell in self._cell_index.values():
            cell.infos = []

    def resolve_date_keys(self, date_str: DateValue, end_date: DateValue = "") -> List[str]:
        """把起始日期（+可选结束日期）展开成日期字符串列表"""
        start = self.parse_date(date_str)
        if not end_date:
            return [format_date_str(start)]

        end = self.parse_date(end_date)
        if end < start:
            start, end = end, start

        # 用序号直接算，避免逐天做 timedelta 加法
        start_no = start.toordinal()
        days = end.toordinal() - start_no + 1
        return [format_date_str(date.fromordinal(start_no + i)) for i in range(days)]

    @staticmethod
    def format_key(date_str: DateValue) -> str:
        return format_date_key(date_str)

    @staticmethod
    def parse_date(date_str: DateValue) -> date:
        """把 YYYY-MM-DD 字符串或 date/datetime 对象统一转成 date"""
        if isinstance(date_str, datetime):
            return date_str.date()
        if isinstance(date_str, date):
            return date_str
        return date.fromisoformat(str(date_str))

    # ---------- 构建 ----------

    def get_month_days(self) -> int:
        """当月的天数"""
        if self.month == 12:
            return 31
        last = date(self.year, self.month + 1, 1) - timedelta(days=1)
        return last.day

    @property
    def weeks(self) -> List[List[CalendarCell]]:
        """按周组织的单元格（6 行 * 7 列），首次访问时才构建"""
        if self._weeks is None:
            self.build_weeks()
        return self._weeks or []

    def build_weeks(self) -> List[List[CalendarCell]]:
        """按周构建单元格，前后补齐相邻月份的日期，保证是完整的 7 列

        只有初始化、年月变化、或者需要整体重排时才调用；
        平时 add_xxx / remove_xxx 走增量更新，不会触发这里。
        """
        first_day = date(self.year, self.month, 1)
        # weekday(): 周一=0 ... 周日=6
        offset = (first_day.weekday() - self.week_start) % 7
        start = first_day - timedelta(days=offset)

        # 6 行 * 7 列，保证不同月份的月历高度一致
        cells: List[CalendarCell] = []
        index: Dict[str, CalendarCell] = {}
        for i in range(42):
            cur_date = start + timedelta(days=i)
            in_month = cur_date.month == self.month and cur_date.year == self.year
            cell = CalendarCell(day=cur_date.day, cur_date=cur_date, in_month=in_month)
            cell.is_today = cur_date == self.today
            # 直接复用 date_infos 里的 list，后续追加信息两边都能看到
            cell.infos = self.date_infos.get(cell.date_str) or []
            cells.append(cell)
            index[cell.date_str] = cell

        self._cell_index = index
        weeks = [cells[i:i + 7] for i in range(0, len(cells), 7)]
        self._weeks = weeks
        return weeks

    # ---------- 年月切换 ----------

    def get_prev_month(self) -> Tuple[int, int]:
        if self.month > 1:
            return self.year, self.month - 1
        return self.year - 1, 12

    def get_next_month(self) -> Tuple[int, int]:
        if self.month < 12:
            return self.year, self.month + 1
        return self.year + 1, 1

    def build_url(self, year: int = 0, month: int = 0) -> str:
        if not self.base_url:
            return ""
        params = dict(self.params)
        params["year"] = year
        params["month"] = month
        sep = "&" if "?" in self.base_url else "?"
        return self.base_url + sep + urlencode(params)

    @property
    def prev_url(self) -> str:
        year, month = self.get_prev_month()
        return self.build_url(year, month)

    @property
    def next_url(self) -> str:
        year, month = self.get_next_month()
        return self.build_url(year, month)

    @property
    def today_url(self) -> str:
        return self.build_url(self.today.year, self.today.month)

    @property
    def param_items(self) -> List[Tuple[str, Any]]:
        return sorted(self.params.items())

    @property
    def year_options(self) -> List[int]:
        return list(range(self.year - self.year_range, self.year + self.year_range + 1))

    @property
    def month_options(self) -> List[int]:
        return list(range(1, 13))

    @property
    def week_labels(self) -> List[str]:
        labels: List[str] = ["一", "二", "三", "四", "五", "六", "日"]
        if self.week_start == 6:
            return ["日"] + labels[:6]
        return labels

    @property
    def title(self) -> str:
        """标题文字，未指定时用「YYYY年M月」"""
        if self._title:
            return self._title
        return "%s年%s月" % (self.year, self.month)

    def render(self):
        return self._code.generate(calendar=self)

