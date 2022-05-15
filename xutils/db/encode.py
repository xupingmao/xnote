# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/04/05 21:12:09
# @modified 2022/04/09 11:00:26
# @filename encode.py

import json
import xutils
from xutils import Storage

INT64_MAX = (1 << 63)-1
INT32_MAX = (1 << 31)-1
INT16_MAX = (1 << 15)-1

def encode_int(int_val):
    """把整型转换成字符串，比较性保持不变
    >>> encode_int(10) > encode_int(1)
    True
    >>> encode_int(12) == encode_int(12)
    True
    >>> encode_int(-1) > encode_int(-10)
    True
    >>> encode_int(12) > encode_int(-1)
    True
    >>> encode_int(10**5) > encode_int(1)
    True
    >>> encode_int(1 << 40) > encode_int(1 << 20)
    True
    >>> encode_int(-(1<<40)) < encode_int(1 << 20)
    True
    >>> encode_int(-(1<<40)) < encode_int(-(1<<20))
    True
    """
    if not isinstance(int_val, int):
        raise Exception("encode_int: expect int but see: (%r)" % int_val)
    if abs(int_val) > INT64_MAX:
        raise Exception("encode_int: int value must between [-%s, %s]" % (INT64_MAX, INT64_MAX))
    
    # 使用16进制文本表达，在可读性和存储空间之间折中。
    # 第一位数字表示数字范围，负数需要放在前面
    # 5: [-INT64_MAX, -INT32_MAX)
    # 6: [-INT32_MAX, -INT16_MAX)
    # 7: [-INT16_MAX, 0)
    # 8: [0, INT16_MAX]
    # 9: (INT16_MAX, INT32_MAX)
    # A: (INT32_MAX, INT64_MAX]

    ## int16
    if 0 <= int_val <= INT16_MAX:
        return "8%04X" % int_val
    
    if -INT16_MAX <= int_val < 0:
        return "7%04X" % (int_val + INT16_MAX)
    
    ## int32
    if 0 <= int_val <= INT32_MAX:
        return "9%08X" % int_val
    
    if -INT32_MAX <= int_val < 0:
        return "6%08X" % (int_val + INT32_MAX)

    ## int64
    if INT32_MAX < int_val <= INT64_MAX:
        return "A%08X" % int_val
    
    if -INT64_MAX <= int_val < -INT32_MAX:
        return "5%08X" % (int_val + INT64_MAX)

    raise Exception("encode_int: invalid value(%d)" % int_val)
    
def encode_int8_to_bytes(int_val):
    assert int_val >= 0
    assert int_val <= 255
    return bytes([int_val])

def encode_float(value):
    """把浮点数编码成字符串
    >>> encode_float(10.5) > encode_float(5.5)
    True
    >>> encode_float(10.5) > encode_float(-10.5)
    True
    >>> encode_float(-0.5) > encode_float(-1.5)
    True
    """
    if value < 0:
        value += 10**20
        return "A%020.10f" % value
    else:
        return "B%020.10f" % value

def encode_str(value):
    """编码字符串
    >>> encode_str("a:b")
    'a%58b'
    >>> encode_str("a%b")
    'a%20b'
    >>> encode_str("中文123")
    '中文123'
    """
    value = value.replace("%", "%20")
    value = value.replace(":", "%58")
    return value

def decode_str(value):
    value = value.replace("%58", ":")
    value = value.replace("%20", "%")
    return value

def encode_index_value(value):
    if value is None:
        return chr(0)
    if isinstance(value, str):
        return encode_str(value)
    if isinstance(value, int):
        return encode_int(value)
    if isinstance(value, float):
        return encode_float(value)
    raise Exception("unknown index_type:%r" % type(value))

def _encode_json(obj):
    """基本类型不会拦截"""
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    return obj

def convert_object_to_json(obj):
    # ensure_ascii默认为True，会把非ascii码的字符转成\u1234的格式
    return json.dumps(obj, ensure_ascii=False, default=_encode_json)

def convert_object_to_bytes(obj):
    return convert_object_to_json(obj).encode("utf-8")

def convert_bytes_to_object(bytes, parse_json=True):
    if bytes is None:
        return None
    str_value = bytes.decode("utf-8")

    if not parse_json:
        return str_value

    try:
        obj = json.loads(str_value)
    except:
        xutils.print_exc()
        return str_value
    if isinstance(obj, dict):
        obj = Storage(**obj)
    return obj
