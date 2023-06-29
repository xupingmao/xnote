# -*- coding:utf-8 -*-
"""
@Author       : kylen66
@email        : kylen66
@Date         : 2023-06-27 23:19:07
@LastEditors  : xupingmao
@LastEditTime : 2023-06-29 23:19:54
@FilePath     : /xnote/xutils/jsonutil.py
@Description  : 描述
"""

import json
import uuid
from datetime import datetime
from datetime import date

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, type(bytes)):
            return str(obj, encoding='utf-8')
        elif isinstance(obj,uuid.UUID):
            return obj.hex
        else:
            return json.JSONEncoder.default(self, obj)
