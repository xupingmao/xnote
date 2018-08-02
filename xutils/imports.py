# -*- coding:utf-8 -*-
# 专门用来import各种依赖
# @author xupingmao <578749341@qq.com>
# @since 2018/06/07 22:12:44
# @modified 2018/08/02 22:33:13
from __future__ import print_function
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
import six
import web
import xconfig
import subprocess
import pickle
from collections import deque
from fnmatch import fnmatch
from tornado.escape import xhtml_escape        
from web.utils import safestr, safeunicode

try:
    import sqlite3
except ImportError:
    sqlite3 = None # jython

try:
    import bs4
except ImportError:
    bs4 = None

PY2 = sys.version_info[0] == 2

if PY2:
    from urllib import quote, unquote, urlopen
    from ConfigParser import ConfigParser
    from StringIO import StringIO
    from Queue import Queue, PriorityQueue
    # from commands import getstatusoutput

    def u(s, encoding="utf-8"):
        if isinstance(s, str):
            return s.decode(encoding)
        elif isinstance(s, unicode):
            return s
        return str(s)

    def listdir(dirname):
        names = list(os.listdir(dirname))
        encoding = sys.getfilesystemencoding()
        return [newname.decode(encoding) for newname in names]

    def is_str(s):
        return isinstance(s, (str, unicode))
else:
    from urllib.parse import quote, unquote
    from urllib.request import urlopen
    from subprocess import getstatusoutput
    from configparser import ConfigParser
    from io import StringIO
    from queue import Queue, PriorityQueue

    u = str
    listdir = os.listdir

    def is_str(s):
        return isinstance(s, str)

# 关于Py2的getstatusoutput，实际上是对os.popen的封装
# 而Py3中的getstatusoutput则是对subprocess.Popen的封装
# Py2的getstatusoutput, 注意原来的windows下不能正确运行，但是下面改进版的可以运行

if PY2:
    def getstatusoutput(cmd):
        """Return (status, output) of executing cmd in a shell."""
        import os
        # old
        # pipe = os.popen('{ ' + cmd + '; } 2>&1', 'r')
        # 这样修改有一个缺点就是执行多个命令的时候只能获取最后一个命令的输出
        pipe = os.popen(cmd + ' 2>&1', 'r')
        text = pipe.read()
        sts = pipe.close()
        if sts is None: sts = 0
        if text[-1:] == '\n': text = text[:-1]
        return sts, text
