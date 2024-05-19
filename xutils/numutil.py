# encoding=utf-8

import uuid

def parse_int(value=""):
    try:
        return int(value)
    except:
        return 0


def parse_float(value=""):
    try:
        return float(value)
    except:
        return 0.0
    

def create_random_int64():
    """创建一个随机的int64值"""
    mask = (1<<64)-1
    id_value = uuid.uuid4().int
    return id_value & mask
