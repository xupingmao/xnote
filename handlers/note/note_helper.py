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
import typing
from xutils import dateutil
from collections import defaultdict
from .models import NoteIndexDO, NoteOptGroup

def assemble_notes_by_date(notes: typing.List[NoteIndexDO], time_attr="ctime"):
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


class NoteGroupConverter:

    def __init__(self, notes: typing.List[NoteIndexDO]):
        self.notes = notes    
        self.note_dict = {} # type: dict[int, NoteIndexDO]
        self.parent_group_dict = {} # type: dict[int, NoteOptGroup]

    def get_group_list_for_create(self):
        notes = self.notes
        sticky_groups   = list(filter(lambda x: x.priority != None and x.priority > 0, notes))
        archived_groups = list(filter(lambda x: x.archived == True, notes))
        normal_groups   = list(filter(lambda x: x not in sticky_groups and x not in archived_groups, notes))

        groups = []

        for item in sticky_groups:
            item.name = u"[置顶]" + item.name
            groups.append(item)

        for item in normal_groups:
            groups.append(item)

        for item in archived_groups:
            item.name = u"[归档]" + item.name
            groups.append(item)

        return groups
    
    def _find_opt_group(self, parent_id=0):
        note_opt_info = self.parent_group_dict.get(parent_id)
        if note_opt_info is not None:
            return note_opt_info
        note_info = self.note_dict.get(parent_id)
        note_opt_info = NoteOptGroup()
        
        if note_info is None:
            note_opt_info.label = "未知"
        else:
            note_opt_info.label = note_info.name

        self.parent_group_dict[parent_id] = note_opt_info
        return note_opt_info
    
    def get_opt_groups(self):
        result = [] # type: list[NoteOptGroup]
        sticky_group = NoteOptGroup()
        sticky_group.label = "置顶"
        root_group = NoteOptGroup()
        root_group.label = "一级目录"
        collected = set()

        note_dict = {} # type: dict[int, NoteIndexDO]
        for note_info in self.notes:
            note_dict[note_info.id] = note_info

            if note_info.is_sticky:
                sticky_group.children.append(note_info)
                collected.add(note_info.id)
            elif note_info.parent_id == 0:
                root_group.children.append(note_info)
                collected.add(note_info.id)
        
        self.note_dict = note_dict
                        
        for note_info in self.notes:
            if note_info.id in collected:
                continue

            if note_info.parent_id > 0:
                # 非一级目录
                parent_group = self._find_opt_group(note_info.parent_id)
                parent_group.children.append(note_info)

        result.append(sticky_group)
        result.append(root_group)

        opt_group_list = self.parent_group_dict.values()
        sorted_opt_group_list = sorted(opt_group_list, key = lambda x:x.label)
        for opt_group in sorted_opt_group_list:
            result.append(opt_group)

        return result
        


