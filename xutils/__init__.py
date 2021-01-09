# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12/09
# @modified 2021/01/09 15:19:38

"""xnote工具类总入口
xutils是暴露出去的统一接口，类似于windows.h一样
建议通过xutils暴露统一接口，其他的utils由xutils导入

"""
from __future__ import print_function
from __future__ import absolute_import

from threading import current_thread
from .imports import *

# xnote工具
import xutils.textutil as textutil
import xutils.ziputil as ziputil
import xutils.fsutil as fsutil
import xutils.logutil as logutil
import xutils.dateutil as dateutil
import xutils.htmlutil as htmlutil

# from . import textutil, ziputil, fsutil, logutil, dateutil, htmlutil
from xutils.ziputil import *
from xutils.netutil import splithost, http_get, http_post
from xutils.textutil import edit_distance, get_short_text, short_text
from xutils.textutil import text_contains, parse_config_text
from xutils.textutil import tojson
from xutils.textutil import mark_text

from xutils.dateutil import *
from xutils.netutil  import *
from xutils.fsutil   import *
from xutils.cacheutil import cache, cache_get, cache_put, cache_del
from xutils.functions import History, MemTable, listremove

# TODO xutils是最基础的库，后续会移除对xconfig的依赖，xutils会提供配置的函数出去在上层进行配置
from xutils.base import Storage
from xutils.logutil import *

import shutil
import logging
import logging.handlers

#################################################################

# 输出缓存区
STDOUT_BUF_SIZE = 1000

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
    exc_info = traceback.format_exc()
    print(exc_info)
    return exc_info

print_stacktrace = print_exc

def print_web_ctx_env():
    for key in web.ctx.env:
        print(" - - %-20s = %s" % (key, web.ctx.env.get(key)))


def print_table_row(row, max_length):
    for item in row:
        print(str(item)[:max_length].ljust(max_length), end='')
    print('')

def print_table(data, max_length=20, headings = None, ignore_attrs = None):
    '''打印表格数据'''
    if len(data) == 0:
        return
    if headings is None:
        headings = list(data[0].keys())
    if ignore_attrs:
        for key in ignore_attrs:
            if key in headings:
                headings.remove(key)
    print_table_row(headings, max_length)
    for item in data:
        row = map(lambda key:item.get(key), headings)
        print_table_row(row, max_length)

class SearchResult(dict):

    def __init__(self, name=None, url='#', raw=None):
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

class MyStdout:

    _instance = None

    """标准输出的装饰器，用来拦截标准输出内容"""
    def __init__(self, stdout, do_print = True):
        self.stdout = stdout
        self.result_dict = dict()
        self.outfile = web.debug
        self.do_print = do_print
        try:
            self.encoding = stdout.encoding
        except:
            print_exc()
        # 全局对象
        MyStdout._instance = self

    def write(self, value):
        result = self.result_dict.get(current_thread())
        if result != None:
            result.append(value)
            if len(result) > STDOUT_BUF_SIZE:
                del result[0]
        if self.do_print:
            print(value, file=self.outfile, end="")

    def writelines(self, lines):
        return self.stdout.writelines(lines)

    def flush(self):
        return self.stdout.flush()

    def close(self):
        return self.stdout.close()

    def record(self):
        # 这里检测TTL
        self.result_dict[current_thread()] = []

    def pop_record(self):
        # 非线程池模式下必须pop_record，不然会有内存泄漏的危险
        # TODO 考虑引入TTL检测机制
        result = self.result_dict.pop(current_thread(), [])
        return "".join(result)

    @staticmethod
    def get_records(thread_obj):
        if MyStdout._instance == None:
            return None
        return MyStdout._instance.result_dict.get(thread_obj)

#################################################################
##   File System Utilities
##   @see fsutil
#################################################################

def is_img_file(filename):
    """根据文件后缀判断是否是图片"""
    if filename.endswith(".x0"):
        filename = fsutil.decode_name(filename)
    name, ext = os.path.splitext(filename)
    return ext.lower() in xconfig.FS_IMG_EXT_LIST

def is_text_file(filename):
    """根据文件后缀判断是否是文本文件"""
    if filename.endswith(".x0"):
        filename = fsutil.decode_name(filename)
    name, ext = os.path.splitext(filename)
    return ext.lower() in xconfig.FS_TEXT_EXT_LIST

def is_audio_file(filename):
    if filename.endswith(".x0"):
        filename = fsutil.decode_name(filename)
    name, ext = os.path.splitext(filename)
    return ext.lower() in xconfig.FS_AUDIO_EXT_LIST

def get_text_ext():
    return xconfig.FS_TEXT_EXT_LIST

def is_editable(fpath):
    return is_text_file(fpath)

def attrget(obj, attr, default_value = None):
    if hasattr(obj, attr):
        return getattr(obj, attr, default_value)
    else:
        return default_value

### DB Utilities

def db_execute(path, sql, args = None):
    from xconfig import Storage
    db = sqlite3.connect(path)
    cursorobj = db.cursor()
    kv_result = []
    try:
        # print(sql)
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


def obj2dict(obj):
    v = {}
    for k in dir(obj):
        if k[0] != '_':
            v[k] = getattr(obj, k)
    return v

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
    """URL安全的base64编码，注意Python自带的方法没有处理填充字符=
    @param str text 待编码的字符
    """
    b64result = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
    return b64result.rstrip("=")


def urlsafe_b64decode(text):
    """URL安全的base64解码，注意Python自带的方法没有处理填充字符=
    @param str text 编码后的字符
    """
    padding = len(text) % 4
    text = text + '=' * padding
    return base64.urlsafe_b64decode(text).decode("utf-8")

b64encode = urlsafe_b64encode
b64decode = urlsafe_b64decode

def encode_uri_component(text):
    # quoted = quote_unicode(text)
    # quoted = quoted.replace("?", "%3F")
    # quoted = quoted.replace("&", "%26")
    # quoted = quoted.replace(" ", "%20")
    # quoted = quoted.replace("=", "%3D")
    # quoted = quoted.replace("+", "%2B")
    # quoted = quoted.replace("#", "%23")
    return quote(text)

def get_safe_file_name(filename):
    """处理文件名中的特殊符号"""
    for c in " @$:#\\|":
        filename = filename.replace(c, "_")
    return filename

def md5_hex(string):
    return hashlib.md5(string.encode("utf-8")).hexdigest()

#################################################################
##   Platform/OS Utilities, Python 2 do not have this file
#################################################################

def system(cmd, cwd = None):
    p = subprocess.Popen(cmd, cwd=cwd, 
                                 shell=True, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
    # out = p.stdout.read()
    # err = p.stderr.read()
    # if PY2:
    #     encoding = sys.getfilesystemencoding()
    #     os.system(cmd.encode(encoding))
    # else:
    #     os.system(cmd)

def is_windows():
    return os.name == "nt"

def is_mac():
    return platform.system() == "Darwin"

def is_linux():
    return os.name == "linux"

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

    msglist = re.split(r"[,.;?!():，。？！；：\n\"'<>《》\[\]]", msg)
    for m in msglist:
        m = m.strip()
        if m == "":
            continue
        cmd = u("say %s") % escape(m)
        trace("MacSay", cmd)
        os.system(cmd.encode("utf-8"))

def windows_say(msg):
    try:
        import comtypes.client as cc
        # dynamic=True不生成静态的Python代码
        voice = cc.CreateObject("SAPI.SpVoice", dynamic=True)
        voice.Speak(msg)
    except ImportError:
        pass
    except:
        print_exc()

def say(msg):
    if xconfig.IS_TEST:
        return
    if is_windows():
        windows_say(msg)
    elif is_mac():
        mac_say(msg)
    else:
        # 防止调用语音API的程序没有正确处理循环
        time.sleep(0.5)

def exec_python_code(name, code, 
        record_stdout = True, 
        raise_err     = False, 
        do_gc         = True, 
        vars          = None):
    ret = None
    try:
        if vars is None:
            vars = {}
        vars["__name__"] = "xscript.%s" % name
        # before_count = len(gc.get_objects())
        if record_stdout:
            if not isinstance(sys.stdout, MyStdout):
                sys.stdout = MyStdout(sys.stdout)
            sys.stdout.record()
        ret = six.exec_(code, vars)
        # 执行一次GC防止内存膨胀
        if do_gc:
            gc.collect()
        # after_count = len(gc.get_objects())
        if record_stdout:
            ret = sys.stdout.pop_record()
        # if do_gc:
        #     log("gc.objects_count %s -> %s" % (before_count, after_count))
        return ret
    except Exception as e:
        print_exc()
        if raise_err:
            raise e
        if record_stdout:
            ret = sys.stdout.pop_record()
        return ret

def fix_py2_code(code):
    if not PY2:
        return code
    # remove encoding declaration, otherwise will cause
    # SyntaxError: encoding declaration in Unicode string
    return re.sub(r'^#[^\r\n]+', '', code)

def exec_script(name, new_window=True, record_stdout = True, vars = None):
    """执行script目录下的脚本"""
    dirname = xconfig.SCRIPTS_DIR
    path    = os.path.join(dirname, name)
    path    = os.path.abspath(path)
    ret     = 0
    if name.endswith(".py"):
        # 方便获取xnote内部信息用于扩展，同时防止开启过多Python进程
        code = xutils.readfile(path)
        code = fix_py2_code(code)
        ret = exec_python_code(name, code, record_stdout, vars = vars)  
    elif name.endswith(".command"):
        # Mac os Script
        xutils.system("chmod +x " + path)
        if new_window:
            ret = xutils.system("open " + path)
        else:
            ret = xutils.system("source " + path)
    elif path.endswith((".bat", ".vbs")):
        if new_window:
            cmd = u("start %s") % path
        else:
            cmd = u("start /b %s") % path
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

def load_script(name, vars = None, dirname = None, code = None):
    """加载脚本
    @param {string} name 插件的名词，和脚本目录(/data/scripts)的相对路径
    @param {dict} vars 全局变量，相当于脚本的globals变量
    @param {dirname} dirname 自定义脚本目录
    @param {code} 指定code运行，不加载文件
    """
    if dirname is None:
        # 必须实时获取dirname
        dirname = xconfig.SCRIPTS_DIR
    if code is None:
        path = os.path.join(dirname, name)
        path = os.path.abspath(path)
        code = readfile(path)
        code = fix_py2_code(code)
    return exec_python_code(name, code, 
        record_stdout = False, raise_err = True, vars = vars)

def exec_command(command, confirmed = False):
    pass

#################################################################
##   Web.py Utilities web.py工具类的封装
#################################################################

def _get_default_by_type(default_value, type):
    if default_value != None:
        return default_value
    if type is bool:
        return False
    return None

def get_argument(key, default_value=None, type = None, strip=False):
    """获取请求参数
    @param {string} key 请求的参数名
    @param {object} default_value 默认值
    @param {type} type 参数类型
    @param {bool} strip 是否过滤空白字符
    """
    if not hasattr(web.ctx, "env"):
        return default_value or None
    ctx_key = "_xnote.input"
    if isinstance(default_value, (dict, list)):
        return web.input(**{key: default_value}).get(key)
    _input = web.ctx.get(ctx_key)
    if _input == None:
        _input = web.input()
        web.ctx[ctx_key] = _input
    value = _input.get(key)
    if value is None or value == "":
        default_value = _get_default_by_type(default_value, type)
        _input[key] = default_value
        return default_value
    if type == bool:
        # bool函数对飞空字符串都默认返回true，需要处理一下
        value = value in ("true", "True", "yes", "Y", "on")
        _input[key] = value
    elif type != None:
        value = type(value)
        _input[key] = value
    if strip and isinstance(value, str):
        value = value.strip()
    return value

#################################################################
##   规则引擎组件
#################################################################

class BaseRule:
    """规则引擎基类"""

    def __init__(self, pattern=None):
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

    def execute(self, ctx, *argv):
        raise NotImplementedError()

class RecordInfo:

    def __init__(self, name, url):
        self.name = name
        self.url  = url

class RecordList:
    """访问记录，可以统计最近访问的，最多访问的记录"""
    def __init__(self, max_size = 1000):
        self.max_size   = max_size
        self.records    = []

    def visit(self, name, url=None):
        self.records.append(RecordInfo(name, url))
        if len(self.records) > self.max_size:
            del self.records[0]

    def recent(self, count=5):
        records = self.records[-count:]
        records.reverse()
        return records

    def most(self, count):
        return []

_funcs = dict()
def register_func(name, func):
    _funcs[name] = func

def call(_func_name, *args, **kw):
    """调用函数
    @param {string} _func_name 方法名
    @param {nargs} *args 可变参数
    @param {kwargs} **kw 关键字参数
    """
    return _funcs[_func_name](*args, **kw)

def lookup_func(name):
    return _funcs[name]

class Module:
    """Module封装"""
    def __init__(self, domain):
        self.domain = domain
        self._meth  = dict()

    def __getattr__(self, key):
        func = self._meth.get(key)
        if func:
            return func
        method = self.domain + "." + key
        func = _funcs[method]
        self._meth[method] = func
        return func
# DAO是模块的别名
DAO = Module

