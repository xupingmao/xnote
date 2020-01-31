# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12/09
# @modified 2020/01/31 12:19:49

"""xnote工具类总入口
xutils是暴露出去的统一接口，类似于windows.h一样
建议通过xutils暴露统一接口，其他的utils由xutils导入

"""
from __future__ import print_function
from threading import current_thread
from .imports import *
# xnote工具
from . import textutil, ziputil, fsutil, logutil, dateutil, htmlutil
from .ziputil import *
from .netutil import splithost, http_get, http_post
from .textutil import edit_distance, get_short_text, short_text
from .dateutil import *
from .netutil  import *
from .fsutil   import *
from .textutil import text_contains, parse_config_text
from .cacheutil import cache, cache_get, cache_put, cache_del
from .functions import History, MemTable, listremove
from xconfig import Storage
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

logger = None
def init_logger():
    global logger
    # filename = os.path.join(xconfig.LOG_DIR, "xnote.log")
    # fmt_str  = '%(asctime)s %(levelname)s %(message)s'
    # fileshandle = logging.handlers.TimedRotatingFileHandler(filename, when='MIDNIGHT', interval=1, backupCount=0)
    # fileshandle.suffix = "%Y-%m-%d"
    # fileshandle.setLevel(logging.DEBUG)
    # formatter = logging.Formatter(fmt_str)
    # fileshandle.setFormatter(formatter)
    # logger = logging.getLogger('')
    # logger.setLevel(logging.INFO)
    # logger.addHandler(fileshandle)

    # logger.info("logger inited!")

def async_func():
    """同步调用转化成异步调用的装饰器"""
    def deco(func):
        def handle(*args, **kw):
            import xmanager
            xmanager.put_task(func, *args, **kw)
        return handle
    return deco

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

def _encode_json(obj):
    """基本类型不会拦截"""
    if inspect.isfunction(obj):
        return "<function>"
    elif inspect.isclass(obj):
        return "<class>"
    elif inspect.ismodule(obj):
        return "<module>"
    return str(obj)


def tojson(obj):
    return json.dumps(obj, default=_encode_json)

#################################################################
##   Html Utilities, Python 2 do not have this file
#################################################################

def set_doctype(type):
    print("#!%s\n" % type)

def get_doctype(text):
    if text.startswith("#!html"):
        return "html"
    return "text"

def mark_text(content):
    """简单的处理HTML"""
    # \xad (Soft hyphen), 用来处理断句的
    content = content.replace(u'\xad', '\n')
    lines = []
    # markdown的LINK样式
    # pat = re.compile(r"\[(.*)\]\((.+)\)")
    for line in content.split("\n"):
        tokens = line.split(" ")
        for index, item in enumerate(tokens):
            if item == "":
                continue
            elif item.startswith(("https://", "http://")):
                tokens[index] = '<a target="_blank" href="%s">%s</a>' % (item, item)
            elif item.startswith("file://"):
                href = item[7:]
                if is_img_file(href):
                    tokens[index] = '<img class="chat-msg-img x-photo" alt="%s" src="%s">' % (href, href)
                else:
                    name = href[href.rfind("/")+1:]
                    # 尝试urldecode名称
                    name = unquote(name)
                    tokens[index] = '<a href="%s">%s</a>' % (href, name)
            elif item.count("#") >=1:
                tokens[index] = re.sub(r"#([^#]+)(#?)", 
                    "<a class=\"link\" href=\"/message?category=message&key=\\g<1>\">#\\g<1>\\g<2></a>", item)
            # elif pat.match(item):
            #     ret = pat.match(item)
            #     name, link = ret.groups()
            #     tokens[index] = '<a href="%s">%s</a>' % (link, name)
            else:
                token = tokens[index]
                token = token.replace("&", "&amp;")
                token = token.replace("<", "&lt;")
                token = token.replace(">", "&gt;")
                tokens[index] = token

        line = '&nbsp;'.join(tokens)
        line = line.replace("\t", '&nbsp;&nbsp;&nbsp;&nbsp;')
        lines.append(line)
    return "<br/>".join(lines)

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

def get_log_path():
    date_time = time.strftime("%Y-%m")
    dirname = os.path.join(xconfig.LOG_DIR, date_time)
    fsutil.makedirs(dirname)
    fname = time.strftime("xnote.%Y-%m-%d.log")
    return os.path.join(dirname, fname)

def log(fmt, show_logger = False, fpath = None, *argv):
    fmt = u(fmt)
    if len(argv) > 0:
        message = fmt.format(*argv)
    else:
        message = fmt
    if show_logger:
        f_back    = inspect.currentframe().f_back
        f_code    = f_back.f_code
        f_modname = f_back.f_globals.get("__name__")
        f_name    = f_code.co_name
        f_lineno  = f_back.f_lineno
        message = "%s %s.%s:%s %s" % (format_time(), f_modname, f_name, f_lineno, message)
    else:
        message = "%s %s" % (format_time(), message)
    print(message)
    if fpath is None:
        fpath = get_log_path()
    log_async(fpath, message)

def _write_log(level, metric, message, cost):
    import xauth
    fpath = get_log_path()
    user_name = xauth.current_name()
    if user_name is None:
        user_name = "-"
    full_message = "%s|%s|%s|%s|%sms|%s" % (format_time(), level, user_name, metric, cost, message)
    # print(full_message)
    # 同步写在SAE上面有巨大的性能损耗
    log_async(fpath, full_message)

def trace(metric, message, cost=0):
    _write_log("TRACE", metric, message, cost)
    

def info(metric, message, cost=0):
    _write_log("INFO", metric, message, cost)

def warn(metric, message, cost=0):
    _write_log("WARN", metric, message, cost)

def error(metric, message, cost=0):
    _write_log("ERROR", metric, message, cost)

@async_func()
def log_async(fpath, full_message):
    with open(fpath, "ab") as fp:
        fp.write((full_message+"\n").encode("utf-8"))

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
##   各种装饰器
#################################################################

def timeit(repeat=1, logfile=False, logargs=False, name="", logret=False):
    """简单的计时装饰器，可以指定执行次数"""
    def deco(func):
        def handle(*args, **kw):
            t1 = time.time()
            for i in range(repeat):
                ret = func(*args, **kw)
            t2 = time.time()
            if logfile:
                message = ""

                if logargs:
                    message = str(args)
                if logret:
                    message = message + "|" + str(ret)
                trace(name, message, int((t2-t1)*1000))
            else:
                print(name, "cost time: ", int((t2-t1)*1000), "ms")
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

