# encoding=utf-8
import logging
import time

def get_prefix():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def debug(fmt, *argv):
    msg = fmt.format(*argv)
    prefix = get_prefix()
    print(prefix, msg)

def info(fmt, *argv):
    msg = fmt.format(*argv)
    prefix = get_prefix()
    print(prefix, msg)

def warn(fmt, *argv):
    msg = fmt.format(*argv)
    prefix = get_prefix()
    print(prefix, msg)

def error(fmt, *argv):
    msg = fmt.format(*argv)
    prefix = get_prefix()
    print(prefix, msg)

def fatal(fmt, *argv):
    msg = fmt.format(*argv)
    prefix = get_prefix()
    print(prefix, msg)