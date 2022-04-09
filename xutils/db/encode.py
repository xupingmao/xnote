# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/04/05 21:12:09
# @modified 2022/04/09 11:00:26
# @filename encode.py

MAX_INT = (1 << 63)-1

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
    """
    if not isinstance(int_val, int):
        raise Exception("encode_int: expect int but see: (%r)" % int_val)
    if abs(int_val) > MAX_INT:
        raise Exception("encode_int: int value must between [-%s, %s]" % (MAX_INT, MAX_INT))
    
    # 负数需要放在前面
    # 使用64位二进制存储
    # 第一位数字表示符号，1表示正数，0表示负数，其余63位可以用于存储数字
    flag = 1 << 63
    if int_val < 0:
        int_val = MAX_INT + int_val
    else:
        int_val = int_val | flag
    
    return "%016X" % int_val

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
