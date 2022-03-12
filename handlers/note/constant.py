# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/02/16 12:49:30
# @modified 2022/03/12 09:39:04

class NoteType:

    def __init__(self, type, name, visible = True):
        self.type = type
        self.name = name
        self.visible = visible

NOTE_TYPE_MAPPING = {
    "document": "md",
    "text"    : "log",
    "post"    : "log",
    "sticky"  : "md",
    "plan"    : "md",
}

NOTE_TYPE_LIST = [
    NoteType("group"  , u"笔记本"),
    NoteType("md"     , u"markdown文档"),
    NoteType("html"   , u"富文本", False),
    NoteType("csv"    , u"表格", True),
    NoteType("list"   , u"清单"),
    NoteType("gallery", u"相册"),
    NoteType("form"   , u"表单", False),
]

NOTE_TYPE_DICT = {}
# 有效的笔记类型
VALID_NOTE_TYPE_SET = set()
for item in NOTE_TYPE_LIST:
    NOTE_TYPE_DICT[item.type] = item.name
    VALID_NOTE_TYPE_SET.add(item.type)

# 其他特殊类型
NOTE_TYPE_DICT["sticky"]      = u"置顶"
NOTE_TYPE_DICT["public"]      = u"公共笔记"
NOTE_TYPE_DICT["removed"]     = u"回收站"
NOTE_TYPE_DICT["recent_edit"] = u"最近编辑"
NOTE_TYPE_DICT["search"]      = u"笔记搜索"
NOTE_TYPE_DICT["document"]    = u"文档"
NOTE_TYPE_DICT["log"]         = u"日志"
NOTE_TYPE_DICT["root_notes"]  = u"默认笔记本"

# 创建按钮文字
CREATE_BTN_TEXT_DICT = {
    "gallery" : u"新建相册",
    "list"    : u"新建清单",
    "document": u"新建文档",
    "table"   : u"新建表格",
    "csv"     : u"新建表格",
    "plan"    : u"新建计划",
    "html"    : u"新建富文本",
    "sticky"  : u"新建文档",
    "log"     : u"新建日志",
    "form"    : u"新建表单",
}

