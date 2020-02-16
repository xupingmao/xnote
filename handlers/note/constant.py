# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/02/16 12:49:30
# @modified 2020/02/16 13:05:36

class NoteType:

    def __init__(self, type, name):
        self.type = type
        self.name = name

NOTE_TYPE_MAPPING = {
    "document": "md",
    "text": "log",
    "post": "log",
}

NOTE_TYPE_LIST = [
    NoteType("group", "项目"),
    NoteType("md", "Markdown"),
    NoteType("html", "富文本"),
    NoteType("csv", "表格"),
    NoteType("list", "清单"),
    NoteType("gallery", "相册"),
    NoteType("log", "日志"),
    NoteType("plan", "计划"),
]

NOTE_TYPE_DICT = {}
for item in NOTE_TYPE_LIST:
    NOTE_TYPE_DICT[item.type] = item.name

# 有效的笔记类型
VALID_NOTE_TYPE_SET = NOTE_TYPE_DICT.keys()
