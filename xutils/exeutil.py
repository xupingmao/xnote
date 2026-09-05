# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/19 16:09:13
# @modified 2022/04/16 08:43:45


"""脚本执行相关的代码"""

import typing
import gc
import sys
import os
import re
import threading
import logging
from collections import deque

import web
from xutils import u

def get_current_thread():
    return threading.current_thread()

def xutils_print_exc():
    import xutils
    xutils.print_exc()

class MyStdout(threading.local):

    # 输出缓存区
    BUF_SIZE = 200

    """标准输出的装饰器，用来拦截标准输出内容
       
    *本类是线程安全的*
    """
    def __init__(self, stdout, do_print = True):
        self.stdout   = stdout
        self.outfile  = web.debug
        self.do_print = do_print
        self.buf      = deque()
        try:
            self.encoding = stdout.encoding
        except:
            xutils_print_exc()
        # 全局对象

    def write(self, value):
        result = self.buf
        if result != None:
            result.append(value)
            if len(result) > self.BUF_SIZE:
                result.popleft()
        if self.do_print:
            print(value, file=self.outfile, end="")

    def writelines(self, lines):
        return self.stdout.writelines(lines)

    def flush(self):
        return self.stdout.flush()

    def close(self):
        return self.stdout.close()

    def record(self):
        self.buf = deque()

    def pop_record(self):
        return "".join(self.buf)

    @staticmethod
    def get_records(thread_obj):
        raise Exception("deprecated!!!")

def exec_python_code(
        name: str, 
        code: str, 
        record_stdout = True, 
        raise_err     = False, 
        do_gc         = True,
        fpath         = None, 
        vars          = None):
    """执行python代码

    :param name: 脚本的名称
    :type name: str
    :param code: 脚本代码
    :type code: str
    :param record_stdout: 是否记录标准输出
    :param raise_err: 是否抛出异常
    :param do_gc: 是否执行GC
    :type do_gc: bool
    :param fpath: 设置的__file__变量
    :type fpath: str|None
    :param vars: 执行的参数
    :type vars: dict|None
    """
    ret = None
    try:
        if vars is None:
            vars = {}
        vars["__name__"] = "xscript.%s" % name
        if fpath != None:
            vars["__file__"] = fpath

        # before_count = len(gc.get_objects())
        if record_stdout:
            if not isinstance(sys.stdout, MyStdout):
                sys.stdout = MyStdout(sys.stdout)
            sys.stdout.record()
        ret = exec(code, vars)
        # 执行一次GC防止内存膨胀
        if do_gc:
            gc.collect()
        # after_count = len(gc.get_objects())
        if isinstance(sys.stdout, MyStdout):
            ret = sys.stdout.pop_record()
        # if do_gc:
        #     log("gc.objects_count %s -> %s" % (before_count, after_count))
        return ret
    except Exception as e:
        logging.error("exception script.name=%s", name)
        xutils_print_exc()
        if raise_err:
            raise e
        if isinstance(sys.stdout, MyStdout):
            ret = sys.stdout.pop_record()
        return ret

def fix_py2_code(code):
    return code

def exec_script(name: str, new_window=True, record_stdout = True, vars = None):
    """执行script目录下的脚本"""
    from xnote.core import xconfig
    import xutils

    dirname = xconfig.SCRIPTS_DIR
    fpath   = os.path.join(dirname, name)
    fpath   = os.path.abspath(fpath)
    path    = fpath
    ret     = 0
    if name.endswith(".py"):
        # 方便获取xnote内部信息用于扩展，同时防止开启过多Python进程
        code = xutils.readfile(path)
        code = fix_py2_code(code)
        ret = exec_python_code(name, code, record_stdout, fpath = fpath, vars = vars)  
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
        os.system(cmd)
    elif path.endswith(".sh"):
        # os.system("chmod +x " + path)
        # os.system(path)
        code = xutils.readfile(path)
        # TODO 防止进程阻塞
        ret, out = xutils.getstatusoutput(code)
        return out
    return ret

def _load_script_code_by_fpath(fpath: str):
    import xutils
    code  = xutils.readfile(fpath)
    code  = fix_py2_code(code)
    return code

def _load_script_code(name: str, dirname: typing.Optional[str] = None):
    """加载脚本代码"""
    from xnote.core import xconfig
    if dirname is None:
        # 必须实时获取dirname
        dirname = xconfig.SCRIPTS_DIR
    fpath = os.path.join(dirname, name)
    return _load_script_code_by_fpath(fpath)

def load_script(name: str, vars: typing.Optional[dict] = None, 
                dirname: typing.Optional[str] = None, code = None):
    """加载脚本文件

    :param name: 插件的名称，和脚本目录(/data/scripts)的相对路径
    :type name: str
    :param vars: 全局变量，相当于脚本的globals变量
    :type vars: dict | None
    :param dirname: 自定义脚本目录
    :type dirname: str | None
    :param code: 指定code运行，不加载文件
    :type code: str | None
    """
    code = _load_script_code(name, dirname)
    return exec_python_code(name, code, 
        record_stdout = False, raise_err = True, vars = vars)


class ScriptMeta:
    """脚本的meta信息处理
    """

    def __init__(self):
        self.meta_dict = dict()
        # list的meta信息，比如
        # @category file
        # @category code
        # 解析为 category = [file, code]
        self.meta_list_dict = dict()

    def add_item(self, key, value):
        # 如果有多个，取第一个
        if key not in self.meta_dict:
            self.meta_dict[key] = value

    def add_list_item(self, key, value):
        item_list = self.meta_list_dict.get(key)
        if item_list is None:
            item_list = []

        item_list.append(value)

        self.meta_list_dict[key] = item_list

    def load_meta_by_fpath(self, fpath: str):
        code = _load_script_code_by_fpath(fpath)
        return self.load_meta_by_code(code)

    def load_meta_by_code(self, code: str):
        for line in code.split("\n"):
            if not line.startswith("#"):
                continue
            line = line.lstrip("#\t ")
            if not line.startswith("@"):
                continue

            line = line.lstrip("@")
            # 去掉注释部分
            meta_line  = line.split("#", 1)[0]
            # 拆分元数据
            meta_parts = meta_line.split(maxsplit = 1)
            meta_key   = meta_parts[0]
            # meta_value = meta_parts[1:]
            if len(meta_parts) == 1:
                meta_value = ''
            else:
                meta_value = meta_parts[1]

            meta_value = meta_value.strip()
            self.add_item(meta_key, meta_value)
            self.add_list_item(meta_key, meta_value)

        return self.meta_dict

    def get_raw_value(self, key: str):
        return self.meta_dict.get(key)

    def get_str_value(self, key, default_value = ""):
        value = self.meta_dict.get(key)
        if value is None:
            return default_value
        else:
            return str(value)

    def get_list_value(self, key):
        value = self.meta_list_dict.get(key)
        if value != None:
            return value

        value = self.meta_dict.get(key)
        if value is None:
            return []
        return [value]

    def get_bool_value(self, key: str, default_value = False):
        value = self.meta_dict.get(key)
        if value is None:
            return default_value
        return "true" == value.lower()

    def get_int_value(self, key, default_value = 0):
        value = self.get_raw_value(key)
        if value is None:
            return default_value
        try:
            return int(value)
        except:
            return default_value

    def get_float_value(self, key: str, default_value = 0.0):
        value = self.get_raw_value(key)
        if value is None:
            return default_value
        try:
            return float(value)
        except:
            return default_value

    def has_tag(self, key):
        return key in self.meta_dict

def load_script_meta(fpath: str):
    meta_object = ScriptMeta()
    meta_object.load_meta_by_fpath(fpath)
    return meta_object

def load_script_meta_by_code(code: str):
    meta_object = ScriptMeta()
    meta_object.load_meta_by_code(code)
    return meta_object
