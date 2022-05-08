# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-04 19:55:32
@LastEditors  : xupingmao
@LastEditTime : 2022-05-04 19:59:37
@FilePath     : /xnote/xutils/db/binlog.py
@Description  : 数据库的binlog,用于同步
"""

import threading

_lock = threading.RLock()

class BinLog:

    def __init__(self) -> None:
        self.last_seq = 0
    
    def add_log(self, optype, key, value):
        with _lock:
            self.last_seq += 1
            pass
