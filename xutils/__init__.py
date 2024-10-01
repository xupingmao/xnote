# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2016/12/09
@LastEditors  : xupingmao
@LastEditTime : 2024-09-01 01:48:16
@FilePath     : /xnote/xutils/__init__.py
@Description  : 描述
"""
from __future__ import print_function
from __future__ import absolute_import


"""xnote工具类总入口
xutils是暴露出去的统一接口，类似于windows.h一样
建议通过xutils暴露统一接口，其他的utils由xutils导入
"""

import shutil
import subprocess
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
from xutils.base import Storage, print_exc, print_stacktrace, XnoteException
from xutils.logutil import *
from xutils.webutil import *
from xutils.exeutil import *
from xutils.func_util import *

FS_IMG_EXT_LIST = []
FS_TEXT_EXT_LIST = []
FS_AUDIO_EXT_LIST = []
FS_CODE_EXT_LIST = []
IS_TEST = False

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

class SearchResult(Storage):
    """搜索结果"""
    def __init__(self, name=None, url='#', raw=None):
        super().__init__()
        self.name = name
        self.url = url
        self.raw = raw # 文本按照原始格式展示在<pre>标签里面
        self.icon = ""
        self.content = ""
        self.show_move = False
        self.show_more_link = False
        self.html = ""
        self.command = "" # 命令类的工具

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

from xutils.osutil import *

#################################################################
##   规则引擎组件
#################################################################

class BaseRule:
    """规则引擎基类"""

    def __init__(self, pattern: str):
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
    
    logutil.init_async_pool(pool_size=pool_size, thread_size=thread_size)
