# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016/12/09
# @modified 2022/04/03 22:15:46

"""xnote工具类总入口
xutils是暴露出去的统一接口，类似于windows.h一样
建议通过xutils暴露统一接口，其他的utils由xutils导入

"""
from __future__ import print_function
from __future__ import absolute_import

import shutil
import logging
import logging.handlers
from threading import current_thread

from xutils.imports import *
# xnote工具
import xutils.textutil as textutil
import xutils.ziputil as ziputil
import xutils.fsutil as fsutil
import xutils.logutil as logutil
import xutils.dateutil as dateutil
import xutils.htmlutil as htmlutil

from xutils.ziputil import *
from xutils.netutil import splithost, http_get, http_post
from xutils.textutil import *
from xutils.dateutil import *
from xutils.netutil  import *
from xutils.fsutil   import *
from xutils.cacheutil import cache, cache_get, cache_put, cache_del
from xutils.functions import History, MemTable, listremove

# TODO xutils是最基础的库，后续会移除对xconfig的依赖，xutils会提供配置的函数出去在上层进行配置
from xutils.base import Storage, print_exc, print_stacktrace
from xutils.logutil import *
from xutils.webutil import *
from xutils.exeutil import *
from xutils.func_util import *

FS_IMG_EXT_LIST = []
FS_TEXT_EXT_LIST = []
FS_AUDIO_EXT_LIST = []
FS_CODE_EXT_LIST = []
IS_TEST = []

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

#################################################################
##   File System Utilities
##   @see fsutil
#################################################################

def do_check_file_type(filename, target_set):
    """根据文件后缀判断是否是图片"""
    if filename.endswith(".x0"):
        filename = fsutil.decode_name(filename)
    name, ext = os.path.splitext(filename)
    return ext.lower() in target_set

def is_img_file(filename):
    """根据文件后缀判断是否是图片"""
    return do_check_file_type(filename, FS_IMG_EXT_LIST)

def is_text_file(filename):
    """根据文件后缀判断是否是文本文件"""
    return do_check_file_type(filename, FS_TEXT_EXT_LIST)

def is_audio_file(filename):
    return do_check_file_type(filename, FS_AUDIO_EXT_LIST)

def is_code_file(filename):
    return do_check_file_type(filename, FS_CODE_EXT_LIST)

def get_text_ext():
    return FS_TEXT_EXT_LIST

def is_editable(fpath):
    return is_text_file(fpath) or is_code_file(fpath)

def attrget(obj, attr, default_value = None):
    if hasattr(obj, attr):
        return getattr(obj, attr, default_value)
    else:
        return default_value

### DB Utilities

def db_execute(path, sql, args = None):
    from xutils.base import Storage
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
    if obj == None:
        return None
    return dict(**obj.__dict__)


def get_safe_file_name(filename):
    """处理文件名中的特殊符号"""
    for c in " @$:#\\|":
        filename = filename.replace(c, "_")
    return filename


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
        logging.warning("没有安装comtypes")
    except:
        print_exc()

def say(msg):
    if IS_TEST:
        return
    if is_windows():
        windows_say(msg)
    elif is_mac():
        mac_say(msg)
    else:
        # 防止调用语音API的程序没有正确处理循环
        time.sleep(0.5)

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


def init(config, pool_size = 2000, thread_size = 5):
    global FS_IMG_EXT_LIST
    global FS_TEXT_EXT_LIST
    global FS_AUDIO_EXT_LIST
    global FS_CODE_EXT_LIST
    global IS_TEST

    FS_TEXT_EXT_LIST  = config.FS_TEXT_EXT_LIST
    FS_IMG_EXT_LIST   = config.FS_IMG_EXT_LIST
    FS_AUDIO_EXT_LIST = config.FS_AUDIO_EXT_LIST
    FS_CODE_EXT_LIST  = config.FS_CODE_EXT_LIST
    IS_TEST           = config.IS_TEST
    
    xutils.webutil.init_webutil_env(is_test = IS_TEST)
    logutil.init_async_pool(pool_size=pool_size, thread_size=thread_size)
