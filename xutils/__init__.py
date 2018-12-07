# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12/09
# @modified 2018/12/08 01:52:42

"""
xnote工具类总入口
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
from .textutil import edit_distance, get_short_text
from .dateutil import *
from .netutil  import *
from .fsutil   import *
from .textutil import text_contains, parse_config_text
from .cacheutil import cache, expire_cache, update_cache
from .functions import History, MemTable, listremove
from xconfig import Storage
import shutil

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

class MyStdout:
    """
    标准输出的装饰器，用来拦截标准输出内容
    """
    def __init__(self, stdout, do_print = True):
        self.stdout = stdout
        self.result_dict = dict()
        self.outfile = web.debug
        self.encoding = stdout.encoding
        self.do_print = do_print

    def write(self, value):
        result = self.result_dict.get(current_thread())
        if result != None:
            result.append(value)
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
        # 考虑引入TTL检测机制
        result = self.result_dict.pop(current_thread(), [])
        return "".join(result)

#################################################################
##   File System Utilities
#################################################################

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
    if size is None:
        size = os.stat(path).st_size
    if size < 1024:
        return '%sB' % size
    elif size < 1024 **2:
        return '%.2fK' % (float(size) / 1024)
    elif size < 1024 ** 3:
        return '%.2fM' % (float(size) / 1024 ** 2)
    else:
        return '%.2fG' % (float(size) / 1024 ** 3)
    
def get_file_size(path, format=True):
    st = os.stat(path)
    if format:
        return get_pretty_file_size(size = st.st_size)
    return st.st_size

def get_real_path(path):
    if path == None:
        return None
    if xconfig.USE_URLENCODE:
        return quote_unicode(path)
    return path

def remove_file(path, hard = False):
    """
    删除文件，默认软删除，也就是移动到trash目录中
    """
    path = get_real_path(path)
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
            # os.rename(path, destpath)
            # shutil.move 可以跨磁盘分区移动文件
            shutil.move(path, destpath)
        # os.remove(path)
    elif os.path.isdir(path):
        if hard:
            shutil.rmtree(path)
            return
        path = path.rstrip("/")
        basename = os.path.basename(path)
        target = os.path.join(xconfig.TRASH_DIR, basename)
        target = os.path.abspath(target)
        path   = os.path.abspath(path)
        if target == path:
            # 已经在回收站，直接删除文件夹
            shutil.rmtree(path)
        else:
            shutil.move(path, target)

remove = remove_file

def _search_path0(path, key, limit=200):
    result_dirs = []
    result_files = []
    key = key.lower()
    count = 0
    for root, dirs, files in os.walk(path):
        root_len = len(root)
        for f in dirs:
            abspath = os.path.join(root, f)
            if fnmatch(f.lower(), key):
                result_dirs.append(abspath)
                count+=1
                if count >= limit:
                    break
        for f in files:
            abspath = os.path.join(root, f)
            if fnmatch(f.lower(), key):
                result_files.append(abspath)
                count+=1
                if count >= limit:
                    break
        if count >= limit:
            break
    return result_dirs + result_files

def search_path(path, key):
    """
    搜索文件系统，key支持通配符表示，具体见fnmatch模块
    """
    result = []
    quoted_key = quote_unicode(key)
    if key != quoted_key:
        result = _search_path0(path, quoted_key)
    return result + _search_path0(path, key)

def get_upload_file_path(filename, 
        data_dir="/files", 
        replace_exists = False, 
        prefix=""):
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
    if filename == "":
        # get upload directory
        return os.path.abspath(dirname), webpath

    while not replace_exists and os.path.exists(newfilepath):
        name, ext = os.path.splitext(filename)
        # 使用下划线，括号会使marked.js解析图片url失败
        temp_filename = "{}_{}{}".format(name, fileindex, ext)
        newfilepath = dirname + temp_filename
        webpath = "/data{}/{}/{}".format(data_dir, date, temp_filename)
        fileindex+=1
    return os.path.abspath(newfilepath), webpath

def is_img_file(filename):
    """根据文件后缀判断是否是图片"""
    name, ext = os.path.splitext(filename)
    return ext.lower() in xconfig.FS_IMG_EXT_LIST

def is_text_file(filename):
    name, ext = os.path.splitext(filename)
    return ext.lower() in xconfig.FS_TEXT_EXT_LIST

def get_text_ext():
    return xconfig.FS_TEXT_EXT_LIST

def is_editable(filename):
    name, ext = os.path.splitext(filename)
    return ext in get_text_ext()

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

def format_date(seconds=None):
    if seconds is None:
        return time.strftime('%Y-%m-%d')
    elif is_str(seconds):
        date_str = seconds.split(" ")[0]
        return date_str
    else:
        st = time.localtime(seconds)
        return time.strftime('%Y-%m-%d', st)

def days_before(days, format=False):
    seconds = time.time()
    seconds -= days * 3600 * 24
    if format:
        return format_time(seconds)
    return time.localtime(seconds)

def match_time(year = None, month = None, day = None, wday = None, tm = None):
    if tm is None:
        tm = time.localtime()
    if year is not None and year != tm.tm_year:
        return False
    if month is not None and month != tm.tm_mon:
        return False
    if day is not None and day != tm.tm_day:
        return False
    if wday is not None and wday != tm.tm_wday:
        return False
    return True

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
    if hasattr(obj, "__call__"):
        return "<function>"
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
            if item.startswith(("https://", "http://")):
                tokens[index] = '<a href="%s">%s</a>' % (item, item)
            elif item.startswith("file://"):
                href = item[7:]
                if is_img_file(href):
                    tokens[index] = '<a href="%s"><img class="chat-msg-img" src="%s"></a>' % (href, href)
                else:
                    name = href[href.rfind("/")+1:]
                    tokens[index] = '<a href="%s">%s</a>' % (href, name)
            elif item.count("#") >=2:
                tokens[index] = re.sub(r"#([^#]+)#", 
                    "<a class=\"link\" href=\"/message?category=message&key=\\g<1>\">#\\g<1>#</a>", item)
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
        # 32=空格
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
        fpath = xconfig.LOG_PATH
    with open(fpath, "ab") as fp:
        fp.write((message+"\n").encode("utf-8"))


def trace(scene, message, cost=0):
    import xauth
    # print("   ", fmt.format(*argv))
    fpath = xconfig.LOG_PATH
    full_message = "%s|%s|%s|%sms|%s" % (format_time(), 
        xauth.get_current_name(), scene, cost, message)
    print(full_message)
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

def timeit(repeat=1, logfile=False, name=""):
    """简单的计时装饰器，可以指定执行次数"""
    def deco(func):
        def handle(*args):
            t1 = time.time()
            for i in range(repeat):
                ret = func(*args)
            t2 = time.time()
            if logfile:
                log("{} cost time: {} ms", name, int((t2-t1)*1000))
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

def call(name, *args, **kw):
    return _funcs[name](*args, **kw)


