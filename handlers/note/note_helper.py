# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-01-21 23:59:01
@LastEditors  : xupingmao
@LastEditTime : 2023-01-22 00:07:43
@FilePath     : /xnote/handlers/note/note_helper.py
@Description  : 笔记的辅助函数
"""

from xutils import dateutil
from collections import defaultdict

def assemble_notes_by_date(notes, time_attr="ctime"):
    notes_dict = defaultdict(list)
    for note in notes:
        if note.priority == 1:
            notes_dict["置顶"].append(note)
            continue
        if note.priority == 2:
            notes_dict["超级置顶"].append(note)
            continue
        datetime_str = note.get(time_attr)
        cdate = dateutil.format_date(datetime_str)
        notes_dict[cdate].append(note)
        note.badge_info = cdate

    result = []
    for date in notes_dict:
        item = (date, notes_dict[date])
        result.append(item)

    result.sort(key=lambda x: x[0], reverse=True)
    return result
