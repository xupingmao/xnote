# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2025-05-23
@LastEditors  : xupingmao
@LastEditTime : 2024-08-31 23:02:30
@FilePath     : /xnote/xnote_migrate/upgrade_019.py
@Description  : 描述
"""
import logging
import xutils

from xutils import numutil
from xnote.core import xtables, xauth
from xnote_migrate import base
from xutils import dbutil, dateutil
from xutils.db.dbutil_helper import new_from_dict
from handlers.note.dao import NoteDO, create_note, NoteIndexDao
from xnote.service.search_service import SearchHistoryDO, SearchHistoryService, SearchHistoryType
from xutils.base import BaseDataRecord
from handlers.note.dao_tag import NoteTagBindDao, NoteTagInfoDao

def do_upgrade():
    # since v2.9.8
    base.execute_upgrade("20250523_fix_file_info", fix_file_info_replacement)


class FileInfo(BaseDataRecord):
    def __init__(self):
        self.id = 0
        self.ctime = xutils.format_datetime()
        self.mtime = xutils.format_datetime()
        self.fpath = ""
        self.ftype = ""
        self.user_id = 0
        self.fsize = 0
        self.remark = ""
        self.sha256 = ""

def fix_file_info_replacement():
    db = xtables.get_file_info_table()
    for row in db.iter():
        file_info = FileInfo.from_dict(row)
        if "$data" in file_info.fpath:
            new_fpath = file_info.fpath.replace("$data", "${data}")
            db.update(where=dict(id=file_info.id), fpath = new_fpath)