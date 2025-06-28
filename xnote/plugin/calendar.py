from xnote.core import xtemplate
from datetime import date, timedelta
from xutils import textutil

class CalendarItem:
    def __init__(self, date: date, count = 0):
        self.date = date
        self.count = count
        self.css_class = self.calc_css_class(count)
        if count == 0:
            self.tip = "无事发生"
        else:
            self.tip = f"发生了{count}个事件"


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
        self.items = []

class MonthInfo:
    def __init__(self, label="", month = 1, cols = 1):
        self.label = label
        self.month = month
        self.cols = cols

class MonthList:
    def __init__(self):
        self.items = [] # type: list[MonthInfo]

    def add_month(self, month = 0):
        if len(self.items) == 0:
            self.items.append(MonthInfo(label=f"{month}月", month=month, cols=1))
        elif self.items[-1].month != month:
            self.items.append(MonthInfo(label=f"{month}月", month=month, cols=1))
        else:
            self.items[-1].cols += 1

class ContributionStats:
    pass

class ContributionCalendar:

    show_stats = False
    stats = ContributionStats()

    def __init__(self, start_date = date(2020, 1, 1), end_date = date(2020, 12, 31), data = {}):
        self.id = textutil.create_uuid()
        self.rows = [] # type: list[CalendarRow]
        month_list = MonthList()

        start_date = self.resolve_start_date(start_date)
        end_date = self.resolve_end_date(end_date)

        labels = ["一", "二", "三", "四", "五", "六", "日"]
        rows = [CalendarRow(label=x) for x in labels]
        date = start_date
        max_count = 1000
        count = 0
        while date <= end_date and count < max_count:
            if date.weekday() == 0:
                month_list.add_month(date.month)
            row = rows[date.weekday()]
            count = data.get(str(date), 0)
            row.items.append(CalendarItem(date=date, count=count))
            date = date + timedelta(days=1)
            count += 1
        self.rows = rows
        self.month_list = month_list.items

        # 星期占1列, 一个月最多占5列, 最后一个月可能不完整
        cols = len(rows[0].items) + 6
        width = cols * 13 + 1
        self.row_style = f"min-width: {width}px"


    def resolve_end_date(self, date: date):
        if date.weekday == 6:
            return date
        diff = 6 - date.weekday()
        return date + timedelta(days=diff)
    
    def resolve_start_date(self, date: date):
        if date.weekday == 0:
            return date
        return date - timedelta(days = date.weekday())

    def render(self):
        return xtemplate.render("common/date/contribution_calendar.html", calendar = self)

