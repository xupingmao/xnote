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

# 64位浮点数尾数的最大值
FLOAT64_MANTISSA_MAX = (1 << 52) - 1

def encode_int(int_val):
    # type: (int) -> str
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
        return "A%16X" % int_val
    
    if -INT64_MAX <= int_val < -INT32_MAX:
        return "5%16X" % (int_val + INT64_MAX)

    raise Exception("encode_int: invalid value(%d)" % int_val)
    
def encode_int8_to_bytes(int_val):
    assert int_val >= 0
    assert int_val <= 255
    return bytes([int_val])

def encode_float(value):
    """把浮点数编码成字符串, IEEE浮点数编码没有顺序, 一些开源的系统编码方式如下
    - ssdb的zset实现, 没有支持float64, 而是支持int64的score
    - pika的zset实现, 通过自定义的Comparator实现了float64编码的排序
    >>> encode_float(10.5) > encode_float(5.5)
    True
    >>> encode_float(10.5) > encode_float(-10.5)
    True
    >>> encode_float(-0.5) > encode_float(-1.5)
    True
    >>> encode_float(123456789.11) > encode_float(100.5)
    True
    """
    if abs(value) > FLOAT64_MANTISSA_MAX:
        raise Exception("float value must between [-%d,%d]" % (FLOAT64_MANTISSA_MAX, FLOAT64_MANTISSA_MAX))
    
    if value < 0:
        value += FLOAT64_MANTISSA_MAX
        prefix = "A"
    else:
        prefix = "B"
    # 16位整数+小数点+6位小数
    return prefix + "%023.6f" % value

def encode_str(value):
    """编码字符串
    >>> encode_str("a:b")
    'a%3Ab'
    >>> encode_str("a%b")
    'a%25b'
    >>> encode_str("中文123")
    '中文123'
    """
    value = value.replace("%", "%25")
    value = value.replace(":", "%3A")
    return value

def decode_str(value):
    value = value.replace("%3A", ":")
    value = value.replace("%25", "%")
    return value

def encode_str_index(value):
    value = value.replace("%", "%25")
    value = value.replace(":", "%3A")
    value = value.replace(",", "%2C")
    return value

def encode_list(value):
    result = []
    for item in value:
        result.append(encode_index_value(item))
    return ",".join(result)

def encode_index_value(value) -> str:
    if value is None:
        return chr(0)
    if isinstance(value, str):
        return encode_str_index(value)
    if isinstance(value, int):
        return encode_int(value)
    if isinstance(value, float):
        return encode_float(value)
    if isinstance(value, list):
        return encode_list(value)
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

def convert_bytes_to_object_strict(bytes_value=b""):
    """严格转换字节数组到对象"""
    if bytes_value is None:
        return None
    str_value = bytes_value.decode("utf-8")
    obj = json.loads(str_value)
    if isinstance(obj, dict):
        obj = Storage(**obj)
    return obj

def _dict_del(dict, key):
    if key in dict:
        del dict[key]

def clean_value_before_update(value):
    if isinstance(value, dict):
        _dict_del(value, "_id")
        _dict_del(value, "_key")

def encode_id(id_value):
    """对ID进行编码, 第一位是标记位, 起步5位, 指数增长
    数据标志位的好处是可以和正常的数字一样处理
    >>> encode_id(100) > encode_id(50)
    True
    >>> encode_id(10**5+10) > encode_id(20)
    True
    """
    assert isinstance(id_value, int)
    assert id_value > 0
    if id_value < 10**5:
        return "1%05d" % id_value
    
    if id_value < 10**10:
        return "2%010d" % id_value
    
    if id_value < 10**15:
        return "3%015d" % id_value
    
    if id_value < 10**20:
        return "4%020d" % id_value
    
    raise Exception("too large id value")

def encode_id_v1(id_value):
    """对ID进行编码
    >>> encode_id(100) > encode_id(50)
    True
    >>> encode_id(10**5+10) > encode_id(20)
    True
    """
    assert isinstance(id_value, int)
    assert id_value > 0
    if id_value < 10**5:
        return "A%05d" % id_value
    
    if id_value < 10**10:
        return "B%010d" % id_value
    
    if id_value < 10**15:
        return "C%015d" % id_value
    
    if id_value < 10**20:
        return "D%020d" % id_value
    
    raise Exception("too large id value")

def decode_id(id_str):
    """对ID进行解码"""
    assert isinstance(id_str, str)
    assert len(id_str) > 1
    
    num_part = id_str[1:]
    return int(num_part)

def convert_bytes_to_dict(data_bytes):
    # type: (bytes) -> dict[bytes, bytes]
    if data_bytes is None:
        return dict()
    else:            
        value_dict = convert_bytes_to_object(data_bytes)
        result = dict()
        for key in value_dict:
            value = value_dict[key]
            result[key.encode("utf-8")] = value.encode("utf-8")
        return result

def convert_bytes_dict_to_bytes(bytes_dict):
    # type: (dict[bytes, bytes]) -> bytes
    data = dict()
    for key in bytes_dict:
        value = bytes_dict[key]
        data[key.decode("utf-8")] = value.decode("utf-8")
    return convert_object_to_bytes(data)


class KeyParser:
    """针对key进行解码"""
    def __init__(self, key=""):
        self.parts = key.split(":")
        self.index = 0
    
    def pop_left(self):
        if self.index < len(self.parts):
            self.index += 1
            return self.parts[self.index-1]
        return ""
    
    def rest(self):
        return ":".join(self.parts[self.index:])

class KeyDecoder(KeyParser):
    pass
