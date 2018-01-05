# encoding=utf-8

"""
utilities for xnote
xutils是暴露出去的统一接口
如果是一个人开发，可以直接写在这个文件中,
如果是团队开发，依然建议通过xutils暴露统一接口，其他的utils由xutils导入
"""
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

from fnmatch import fnmatch
from util.ziputil import *
from util.textutil import edit_distance

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
    from Queue import Queue
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
else:
    from urllib.parse import quote, unquote
    from urllib.request import urlopen
    from subprocess import getstatusoutput
    from configparser import ConfigParser
    from io import StringIO
    from queue import Queue

    u = str
    listdir = os.listdir

# 关于Py2的getstatusoutput，实际上是对os.popen的封装
# 而Py3中的getstatusoutput则是对subprocess.Popen的封装
# Py2的getstatusoutput, 注意原来的windows下不能正确运行，但是下面改进版的可以运行

from util.dateutil import *
from util.netutil  import *
from util.fsutil   import *
from util.textutil import text_contains

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
from web.utils import safestr, safeunicode

#################################################################


wday_map = {
    "no-repeat": "一次性",
    "*": "每天",
    "1": "周一",
    "2": "周二",
    "3": "周三",
    "4": "周四",
    "5": "周五",
    "6": "周六",
    "7": "周日"
}

def print_exc():
    """打印系统异常堆栈"""
    ex_type, ex, tb = sys.exc_info()
    # print(ex)
    # traceback.print_tb(tb)
    print(traceback.format_exc())

print_stacktrace = print_exc

def print_web_ctx_env():
    for key in web.ctx.env:
        print(" - - %-20s = %s" % (key, web.ctx.env.get(key)))


class Storage(dict):
    """
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
    def __init__(self, default_value=None, **kw):
        self.default_value = default_value
        super(Storage, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as k:
            return self.default_value
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)
    
    def __repr__(self):     
        return '<MyStorage ' + dict.__repr__(self) + '>'


class SearchResult(dict):

    def __init__(self, name=None, url=None, raw=None):
        self.name = name
        self.url = url
        self.raw = raw

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
    last_err = None
    for encoding in ["utf-8", "gbk", "mbcs", "latin_1"]:
        try:
            if PY2:
                with open(path) as fp:
                    content = fp.read()
                    return content.decode(encoding)
            else:
                with open(path, encoding=encoding) as fp:
                    content = fp.read()
                    return content
        except Exception as e:
            last_err = e
    raise Exception("can not read file %s" % path, last_err)
        
def savetofile(path, content):
    import codecs
    with open(path, mode="wb") as fp:
        buf = codecs.encode(content, "utf-8")
        fp.write(buf)
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

def get_real_path(path):
    if not os.path.exists(path):
        return quote_unicode(path)
    return path
    
def makedirs(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def remove(path, hard = False):
    if not os.path.exists(path):
        return
    if os.path.isfile(path):
        if hard:
            os.remove(path)
            return
        dirname = os.path.dirname(path)
        dirname = os.path.abspath(dirname)
        dustbin = os.path.abspath(xconfig.TRASH_DIR)
        if dirname == dustbin:
            os.remove(path)
        else:
            name = os.path.basename(path)
            destpath = os.path.join(dustbin, "%s_%s" % (time.strftime("%Y%m%d"), name))
            os.rename(path, destpath)
        # os.remove(path)
    elif os.path.isdir(path):
        # shutil.rmtree(path)
        os.removedirs(path)

def touch(path):
    """类似于Linux的touch命令"""
    if not os.path.exists(path):
        with open(path, "wb") as fp:
            pass
    else:
        current = time.mktime(time.gmtime())
        times = (current, current)
        os.utime(path, times)

def _search_path0(path, key, limit=200):
    result_dirs = []
    result_files = []
    key = key.lower()
    count = 0
    for root, dirs, files in os.walk(path):
        for f in dirs:
            abspath = os.path.join(root, f)
            if fnmatch(abspath.lower(), key):
                result_dirs.append(abspath)
                count+=1
                if count >= limit:
                    break
        for f in files:
            abspath = os.path.join(root, f)
            if fnmatch(abspath.lower(), key):
                result_files.append(abspath)
                count+=1
                if count >= limit:
                    break
        if count >= limit:
            break
    return result_dirs + result_files

def search_path(path, key):
    result = []
    quoted_key = quote_unicode(key)
    if key != quoted_key:
        result = _search_path0(path, quoted_key)
    return result + _search_path0(path, key)

def get_upload_file_path(filename, data_dir="/files", replace_exists = False, prefix=""):
    """生成上传文件名"""
    if xconfig.USE_URLENCODE:
        filename = get_safe_file_name(filename)
    basename, ext = os.path.splitext(filename)
    date = time.strftime("%Y/%m")
    dirname = xconfig.DATA_PATH + data_dir + "/" + date + "/"

    origin_filename = dirname + filename
    makedirs(dirname)
    fileindex = 1

    if prefix != "" and prefix != None:
        filename = prefix + "_" + filename
        webpath = "/data{}/{}/{}".format(data_dir, date, filename)
        return dirname + filename, webpath
    newfilepath = origin_filename
    webpath = "/data{}/{}/{}".format(data_dir, date, filename)

    while not replace_exists and os.path.exists(newfilepath):
        name, ext = os.path.splitext(filename)
        # 使用下划线，括号会使marked.js解析图片url失败
        temp_filename = "{}_{}{}".format(name, fileindex, ext)
        newfilepath = dirname + temp_filename
        webpath = "/data{}/{}/{}".format(data_dir, date, temp_filename)
        fileindex+=1
    return newfilepath, webpath

def is_img_file(filename):
    """根据文件后缀判断是否是图片"""
    name, ext = os.path.splitext(filename)
    return ext.lower() in (".gif", ".png", ".jpg", ".jpeg", ".bmp")

### DB Utilities

def db_execute(path, sql, args = None):
    db = sqlite3.connect(path)
    cursorobj = db.cursor()
    kv_result = []
    try:
        print(sql)
        if args is None:
            cursorobj.execute(sql)
        else:
            cursorobj.execute(sql, args)
        result = cursorobj.fetchall()
        # result.rowcount
        db.commit()
        for single in result:
            resultMap = Storage()
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

def format_time_only(seconds=None):
    if seconds == None:
        return time.strftime('%H:%M:%S')
    else:
        st = time.localtime(seconds)
        return time.strftime('%H:%M:%S', st)

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

def urlsafe_b64encode(text):
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")

def urlsafe_b64decode(text):
    return base64.urlsafe_b64decode(text.encode("utf-8")).decode("utf-8")

def encode_uri_component(url):
    quoted = quote_unicode(url)
    quoted = quoted.replace("?", "%3F")
    quoted = quoted.replace("&", "%26")
    return quoted

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
    def quote_char(c):
        # ASCII 范围 [0-127]
        # 处理空格 ' '
        if c == 32: 
            return '%20'
        if c <= 127:
            return chr(c)
        return '%%%02X' % c

    if six.PY2:
        bytes = url
        return ''.join([quote_char(ord(c)) for c in bytes])
    else:
        bytes = url.encode("utf-8")
        return ''.join([quote_char(c) for c in bytes])

    # def urlencode(matched):
    #     text = matched.group()
    #     return quote(text)
    # return re.sub(r"[\u4e00-\u9fa5]+", urlencode, url)
    

def get_safe_file_name(filename):
    filename = filename.replace(" ", "_")
    return quote_unicode(filename)

#################################################################
##   Platform/OS Utilities, Python 2 do not have this file
#################################################################

def log(fmt, *argv):
    fmt = str(fmt)
    message = fmt.format(*argv)
    f_back = inspect.currentframe().f_back
    f_code = f_back.f_code
    f_modname = f_back.f_globals.get("__name__")
    f_name = f_code.co_name
    f_lineno = f_back.f_lineno
    message = "%s %s.%s:%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), f_modname, f_name, f_lineno, message)
    print(message)
    with open(xconfig.LOG_PATH, "ab") as fp:
        fp.write((message+"\n").encode("utf-8"))


def trace(fmt, *argv):
    print("   ", fmt.format(*argv))

def system(cmd):
    if PY2:
        encoding = sys.getfilesystemencoding()
        os.system(cmd.encode(encoding))
    else:
        os.system(cmd)

def is_windows():
    return os.name == "nt"

def is_mac():
    return platform.system() == "Darwin"

def is_linux():
    return os.name == "linux"

def get_text_ext():
    return (
        ".md", 
        ".csv", 
        ".properties", 
        ".java", 
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".py",
        ".lua",
        ".gradle",
        ".js",
        ".json",
        ".command",
        ".scala",
        ".yml",
        ".php"
    )

def is_editable(filename):
    name, ext = os.path.splitext(filename)
    return ext in get_text_ext()

def http_get(url):
    stream = urlopen(url)
    return decode_bytes(stream.read())

def mac_say(msg):
    def escape(str):
        new_str_list = ['"']
        for c in str:
            if c != '"':
                new_str_list.append(c)
            else:
                new_str_list.append('\\"')
        new_str_list.append('"')
        return ''.join(new_str_list)

    msglist = re.split(r"[,.;?!():，。？！；：\n]", msg)
    for m in msglist:
        m = m.strip()
        if m == "":
            continue
        cmd = u("say %s") % escape(m)
        trace(cmd)
        os.system(cmd.encode("utf-8"))

def windows_say(msg):
    try:
        import comtypes.client as cc
        # dynamic=True不生成静态的Python代码
        voice = cc.CreateObject("SAPI.SpVoice", dynamic=True)
        voice.Speak(msg)
    except:
        pass

def say(msg):
    if xconfig.IS_TEST:
        return
    if is_windows():
        windows_say(msg)
    elif is_mac():
        mac_say(msg)
    else:
        # 防止调用语音API的程序没有正确处理循环
        time.sleep(1)


def exec_script(name):
    """执行script目录下的脚本"""
    dirname = xconfig.SCRIPTS_DIR
    path = os.path.join(dirname, name)
    path = os.path.abspath(path)
    ret  = 0
    if name.endswith(".py"):
        try:
            # 方便获取xnote内部信息，同时防止开启过多Python进程
            code = xutils.readfile(path)
            globals_copy = {"__name__": "__main__"}
            before_count = len(gc.get_objects())
            # exec(code, globals, locals) locals的作用是为了把修改传递回来
            sys.stdout.record()
            ret = six.exec_(code, globals_copy)
            del globals_copy
            # 执行一次GC防止内存膨胀
            gc.collect()
            after_count = len(gc.get_objects())
            ret = sys.stdout.pop_record()
            log("gc.objects_count %s -> %s" % (before_count, after_count))
        except:
            print_stacktrace()
            ret = sys.stdout.pop_record()
    elif name.endswith(".command"):
        # Mac os Script
        xutils.system("chmod +x " + path)
        ret = xutils.system("open " + path)
    elif path.endswith((".bat", ".vbs")):
        cmd = u("start %s") % path
        if six.PY2:
            # Python2 import当前目录优先
            encoding = sys.getfilesystemencoding()
            cmd = cmd.encode(encoding)
        os.system(cmd)
    elif path.endswith(".sh"):
        # os.system("chmod +x " + path)
        # os.system(path)
        code = readfile(path)
        # TODO 防止进程阻塞
        ret, out = getstatusoutput(code)
        return out
    return ret


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
    if value is None or value == "":
        _input[key] = default_value
        return default_value
    if type != None:
        value = type(value)
        _input[key] = value
    if strip and isinstance(value, str):
        value = value.strip()
    return value


#################################################################
##   各种装饰器
#################################################################

def timeit(repeat=1):
    """简单的计时装饰器，可以指定执行次数"""
    def deco(func):
        def handle(*args):
            t1 = time.time()
            for i in range(repeat):
                ret = func(*args)
            t2 = time.time()
            print("cost time", t2-t1)
            return ret
        return handle
    return deco

def profile():
    """Profile装饰器,打印信息到标准输出,不支持递归函数"""
    def deco(func):
        def handle(*args, **kw):
            if xconfig.OPEN_PROFILE:
                vars = dict()
                vars["_f"] = func
                vars["_args"] = args
                vars["_kw"] = kw
                pf.runctx("r=_f(*_args, **_kw)", globals(), vars, sort="time")
                return vars["r"]
            return func(*args, **kw)
        return handle
    return deco

_cache_dict = dict()

class CacheObj:
    _queue = Queue()

    def __init__(self, key, value, expire):
        global _cache_dict
        self.key = key
        self.value = value
        self.expire = expire
        self.expire_time = time.time() + expire
        self.is_force_expired = False

        if expire < 0:
            self.expire_time = -1

        _cache_dict[key] = self
        self._queue.put(self)
        one = self._queue.get(block=False)
        if one is not None:
            if one.is_force_expired == True:
                return
            if one.is_alive():
                self._queue.put(one)
            else:
                one.clear()

    def is_alive(self):
        if self.expire_time < 0:
            return True
        return time.time() < self.expire_time

    def clear(self):
        # print("cache %s expired" % self.key)
        _cache_dict.pop(self.key, None)

def cache(key=None, prefix=None, expire=600):
    """缓存的装饰器，会自动清理失效的缓存
    TODO 可以考虑缓存持久化的问题
    """
    def deco(func):
        # 先不支持keywords参数
        def handle(*args):
            if key is not None:
                cache_key = key
            elif prefix is None:
                mod = inspect.getmodule(func)
                funcname = func.__name__
                cache_key = "%s.%s%s" % (mod.__name__, funcname, args)
            else:
                cache_key = "%s%s" % (prefix, args)
            obj = _cache_dict.get(cache_key)
            if obj != None and obj.is_alive():
                # print("hit cache %s" % cache_key)
                return obj.value
            if obj != None and not obj.is_alive():
                obj.clear()
            value = func(*args)
            CacheObj(cache_key, value, expire)
            return value
        return handle
    return deco


def expire_cache(key):
    """使key对应的缓存失效，成功返回True"""
    obj = _cache_dict.get(key)
    if obj != None:
        # 防止删除了新的cache
        obj.clear()
        obj.is_force_expired = True
        return True
    return False


#################################################################
##   规则引擎组件
#################################################################

class BaseRule:
    """规则引擎基类"""

    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, ctx, input_str = None):
        if input_str is not None:
            return re.match(self.pattern, input_str)
        return None

    def match_execute(self, ctx, input_str = None):
        try:
            matched = self.match(ctx, input_str)
            if matched:
                self.execute(ctx, *matched.groups())
        except Exception as e:
            print_exc()

    def execute(self, ctx):
        raise NotImplementedError()

