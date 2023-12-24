# encoding=utf-8

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