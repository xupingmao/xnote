# -*- coding:utf-8 -*-
"""
@Author       : kylen66
@email        : kylen66
@Date         : 2023-06-27 23:19:07
@LastEditors  : xupingmao
@LastEditTime : 2024-05-19 11:56:07
@FilePath     : /xnote/xutils/jsonutil.py
@Description  : 描述
"""

import json
import uuid
import inspect
import typing
import base64

from datetime import datetime
from datetime import date

class MyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, bytes):
            # 对于非法的utf-8字符使用转义字符表示
            return str(obj, encoding='utf-8', errors='backslashreplace')
        if isinstance(obj,uuid.UUID):
            return obj.hex
        if inspect.isfunction(obj):
            return "<function>"
        if inspect.isclass(obj):
            return "<class>"
        if inspect.ismodule(obj):
            return "<module>"

        return str(obj)


def parse_json_to_dict(text: typing.Union[str, bytes]):
    """json转dict"""
    result = json.loads(text)
    assert isinstance(result, dict)
    return result

def tojson(obj, ensure_ascii=False, format=False):
    """对象转json"""
    separators=(',', ':')
    if format:
        return json.dumps(obj, cls=MyEncoder, sort_keys=True, indent=2, 
                          ensure_ascii=ensure_ascii, separators=separators)
    else:
        return json.dumps(obj, cls=MyEncoder, ensure_ascii=ensure_ascii, separators=separators)

