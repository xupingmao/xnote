# -*- coding:utf-8 -*-
# 专门用来import各种依赖
# @author xupingmao <578749341@qq.com>
# @since 2018/06/07 22:12:44
# @modified 2022/04/16 09:05:41
from __future__ import print_function

from . import six
from .six.moves.configparser import ConfigParser
from .six.moves.urllib.parse import quote, unquote
from .six.moves.urllib.request import urlopen
from .six import StringIO

import sys
import os
import traceback
import inspect
import json
import base64
import time
import platform
import re
import gc
import shutil
import profile as pf
import subprocess
import pickle
import hashlib
import codecs
import web

from xutils.base import Storage
from collections import deque
from fnmatch import fnmatch
from xutils.tornado.escape import xhtml_escape
from xutils.base import is_str, try_decode
from web.utils import safestr, safeunicode

try:
    import sqlite3
except ImportError:
    sqlite3 = None # sqlite3 is not available, may be jython

try:
    import bs4
except ImportError:
    bs4 = None

PY2 = sys.version_info[0] == 2

if PY2:
    from Queue import Queue, PriorityQueue
    # from commands import getstatusoutput

    def u(s, encoding="utf-8"):
        if isinstance(s, str):
            return s.decode(encoding)
        elif isinstance(s, unicode):
            return s
        elif isinstance(s, Exception):
            return u(s.message)
        return str(s)

    def listdir(dirname):
        names = list(os.listdir(dirname))
        encoding = sys.getfilesystemencoding()
        return [newname.decode(encoding) for newname in names]
else:
    # Py3 and later
    from subprocess import getstatusoutput
    from queue import Queue, PriorityQueue

    u = str
    listdir = os.listdir


def quote_unicode(url):
    # python的quote会quote大部分字符，包括ASCII符号
    # JavaScript的encodeURI
    # encodeURI 会替换所有的字符，但不包括以下字符，即使它们具有适当的UTF-8转义序列：
    #    类型  包含
    #    保留字符    ; , / ? : @ & = + $
    #    非转义的字符  字母 数字 - _ . ! ~ * ' ( )
    #    数字符号    #
    # 根据最新的RFC3986，方括号[]也是非转义字符
    # JavaScript的encodeURIComponent会编码+,&,=等字符
    def quote_char_by_code(c):
        # ASCII 范围 [0-127]
        # 32=空格
        if c == 32: 
            return '%20'
        if c <= 127:
            return chr(c)
        return '%%%02X' % c

    if six.PY2:
        bytes = url
        return ''.join([quote_char_by_code(ord(c)) for c in bytes])
    else:
        bytes = url.encode("utf-8")
        return ''.join([quote_char_by_code(c) for c in bytes])

    # def urlencode(matched):
    #     text = matched.group()
    #     return quote(text)
    # return re.sub(r"[\u4e00-\u9fa5]+", urlencode, url)
