# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-09 08:54:12
@LastEditors  : xupingmao
@LastEditTime : 2022-07-09 09:18:05
@FilePath     : /xnote/handlers/note/note_fix.py
@Description  : 笔记修复
"""
import xmanager

from .dao_book import fix_book_delete

@xmanager.listen("note.notfound")
def on_fix_not_found(event):
    id = event.id
    user_name = event.user_name
    fix_book_delete(id, user_name)

