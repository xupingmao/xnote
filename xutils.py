# encoding=utf-8

"""
utilities for xnote
xutils是暴露出去的统一接口
如果是一个人开发，可以直接写在这个文件中,
如果是团队开发，依然建议通过xutils暴露统一接口，其他的utils由xutils导入
"""
import sys
import os
import traceback
import sqlite3
import json
import time
import platform
import re
import shutil
import web

from util.ziputil import *

PY2 = sys.version_info[0] == 2

if PY2:
    from urllib import quote, unquote, urlopen
    from ConfigParser import ConfigParser
    # from commands import getstatusoutput
else:
    from urllib.parse import quote, unquote
    from urllib.request import urlopen
    from subprocess import getstatusoutput
    from configparser import ConfigParser

# 关于Py2的getstatusoutput，实际上是对os.popen的封装
# 而Py3中的getstatusoutput则是对subprocess.Popen的封装
# Py2的getstatusoutput, 注意原来的windows下不能正确运行，但是下面改进版的可以运行

if PY2:
    def getstatusoutput(cmd):
        ## Return (status, output) of executing cmd in a shell.
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


from tornado.escape import xhtml_escape        
from web.utils import Storage
from web.utils import safestr, safeunicode

#################################################################


def print_stacktrace():
    """打印系统异常堆栈"""
    ex_type, ex, tb = sys.exc_info()
    print(ex)
    traceback.print_tb(tb)

def print_web_ctx_env():
    for key in web.ctx.env:
        print(" - - %-20s = %s" % (key, web.ctx.env.get(key)))


class SilentStorage(dict):
    """
    A Storage will not raise AttributeError
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
    """
    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError as k:
            return None
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)
    
    def __repr__(self):     
        return '<SilentStorage ' + dict.__repr__(self) + '>'


    
#################################################################
##   File System Utilities
#################################################################
def readfile(path, mode = "r"):
    '''
    读取文件，尝试多种编码，编码别名参考标准库Lib/encodings/aliases.py
        utf-8 是一种边长编码，兼容ASCII
        gbk 是一种双字节编码，全称《汉字内码扩展规范》，兼容GB2312
        latin_1 是iso-8859-1的别名，单字节编码，兼容ASCII
    '''
    for encoding in ["utf-8", "gbk", "mbcs", "latin_1"]:
        try:
            fp = open(path, encoding=encoding)
            content = fp.read()
            fp.close()
            return content
        except:
            pass
    raise Exception("can not read file %s" % path)
        
def savetofile(path, content):
    import codecs
    fp = open(path, mode="wb")
    buf = codecs.encode(content, "utf-8")
    fp.write(buf)
    fp.close()
    return content
    
savefile = savetofile

def backupfile(path, backup_dir = None, rename=False):
    if os.path.exists(path):
        if backup_dir is None:
            backup_dir = os.path.dirname(path)
        name   = os.path.basename(path)
        newname = name + ".bak"
        newpath = os.path.join(backup_dir, newname)
        # need to handle case that bakup file exists
        import shutil
        shutil.copyfile(path, newpath)
        
def get_pretty_file_size(path = None, size = 0):
    if size == 0:
        size = os.stat(path).st_size
    if size < 1024:
        return '%s B' % size
    elif size < 1024 **2:
        return '%.2f K' % (float(size) / 1024)
    elif size < 1024 ** 3:
        return '%.2f M' % (float(size) / 1024 ** 2)
    else:
        return '%.2f G' % (float(size) / 1024 ** 3)
    
def get_file_size(path, format=True):
    st = os.stat(path)
    if format:
        return get_pretty_file_size(size = st.st_size)
    return st.st_size
    
    
def makedirs(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def remove(path):
    if not os.path.exists(path):
        return
    if os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)

def touch(path):
    if not os.path.exists(path):
        with open(path, "wb") as fp:
            pass
    

def db_execute(path, sql, args = None):
    db = sqlite3.connect(path)
    cursorobj = db.cursor()
    kv_result = []
    try:
        if args is None:
            cursorobj.execute(sql)
        else:
            cursorobj.execute(sql, args)
        result = cursorobj.fetchall()
        # result.rowcount
        db.commit()
        for single in result:
            resultMap = {}
            for i, desc in enumerate(cursorobj.description):
                name = desc[0]
                resultMap[name] = single[i]
            kv_result.append(resultMap)

    except Exception as e:
        raise e
    finally:
        db.close()
    return kv_result
#################################################################
##   DateTime Utilities
#################################################################

def format_time(seconds=None):
    if seconds == None:
        return time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        st = time.localtime(seconds)
        return time.strftime('%Y-%m-%d %H:%M:%S', st)

def format_date(seconds=None):
    if seconds is None:
        return time.strftime('%Y-%m-%d')
    else:
        st = time.localtime(seconds)
        return time.strftime('%Y-%m-%d', st)

def format_datetime(seconds=None):
    if seconds == None:
        return time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        st = time.localtime(seconds)
        return time.strftime('%Y-%m-%d %H:%M:%S', st)

def days_before(days, format=False):
    seconds = time.time()
    seconds -= days * 3600 * 24
    if format:
        return format_time(seconds)
    return time.localtime(seconds)

#################################################################
##   Str Utilities
#################################################################

def json_str(**kw):
    return json.dumps(kw)

def decode_bytes(bytes):
    for encoding in ["utf-8", "gbk", "mbcs", "latin_1"]:
        try:
            return bytes.decode(encoding)
        except:
            pass
    return None

#################################################################
##   Html Utilities, Python 2 do not have this file
#################################################################
def html_escape(s, quote=True):
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true (the default), the quotation mark
    characters, both double quote (") and single quote (') characters are also
    translated.
    """
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace('\'', "&#x27;")
    return s

def quote_unicode(url):
    def quote_char(c):
        # ASCII 范围 [0-127]
        if c <= 127:
            return chr(c)
        return '%%%02X' % c

    bytes = url.encode("utf-8")
    return ''.join([quote_char(c) for c in bytes])

    # def urlencode(matched):
    #     text = matched.group()
    #     return quote(text)
    # return re.sub(r"[\u4e00-\u9fa5]+", urlencode, url)
    
#################################################################
##   Platform/OS Utilities, Python 2 do not have this file
#################################################################

def is_windows():
    return os.name == "nt"

def is_mac():
    return platform.system() == "Darwin"

def http_get(url):
    stream = urlopen(url)
    return decode_bytes(stream.read())

def mac_say(msg):
    os.system("say %s" % msg)

def windows_say(msg):
    import comtypes.client as cc
    # dynamic=True不生成静态的Python代码
    voice = cc.CreateObject("SAPI.SpVoice", dynamic=True)
    voice.Speak(msg)

def say(msg):
    if is_windows():
        windows_say(msg)
    elif is_mac():
        mac_say(msg)


#################################################################
##   Web.py Utilities web.py工具类的封装
#################################################################
def get_argument(key, default_value=None, type = None, strip=False):
    if isinstance(default_value, dict):
        return web.input(**{key: default_value}).get(key)
    _input = web.ctx.get("_xnote.input")
    if _input == None:
        _input = web.input()
        web.ctx["_xnote.input"] = _input
    value = _input.get(key)
    if value is None:
        _input[key] = default_value
        return default_value
    if type != None:
        value = type(value)
        _input[key] = value
    if strip and isinstance(value, str):
        value = value.strip()
    return value
