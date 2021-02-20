# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/19 16:09:13
# @modified 2021/02/19 16:50:19


"""脚本执行相关的代码"""
import six
import gc
import sys
import os
import web
import threading
from xutils.imports import PY2

# 输出缓存区
STDOUT_BUF_SIZE = 1000

def get_current_thread():
    return threading.current_thread()

def xutils_print_exc():
    import xutils
    xutils.print_exc()

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
            xutils_print_exc()
        # 全局对象
        MyStdout._instance = self

    def write(self, value):
        result = self.result_dict.get(get_current_thread())
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
        self.result_dict[get_current_thread()] = []

    def pop_record(self):
        # 非线程池模式下必须pop_record，不然会有内存泄漏的危险
        # TODO 考虑引入TTL检测机制
        result = self.result_dict.pop(get_current_thread(), [])
        return "".join(result)

    @staticmethod
    def get_records(thread_obj):
        if MyStdout._instance == None:
            return None
        return MyStdout._instance.result_dict.get(thread_obj)

def exec_python_code(
        name, 
        code, 
        record_stdout = True, 
        raise_err     = False, 
        do_gc         = True,
        fpath         = None, 
        vars          = None):
    """执行python代码
    @param {string} name 脚本的名称
    @param {string} code 脚本代码
    @param {bool} record_stdout 是否记录标准输出
    @param {bool} raise_err 是否抛出异常
    @param {bool} do_gc 是否执行GC
    @param {dict} vars 执行的参数
    """
    import xutils
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
        xutils_print_exc()
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
    import xconfig
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
        if six.PY2:
            # Python2 import当前目录优先
            encoding = sys.getfilesystemencoding()
            cmd = cmd.encode(encoding)
        os.system(cmd)
    elif path.endswith(".sh"):
        # os.system("chmod +x " + path)
        # os.system(path)
        code = xutils.readfile(path)
        # TODO 防止进程阻塞
        ret, out = getstatusoutput(code)
        return out
    return ret

def _load_script_code_by_fpath(fpath):
    import xutils
    code  = xutils.readfile(fpath)
    code  = fix_py2_code(code)
    return code

def _load_script_code(name, dirname = None):
    """加载脚本代码"""
    import xconfig
    import xutils
    if dirname is None:
        # 必须实时获取dirname
        dirname = xconfig.SCRIPTS_DIR
    fpath = os.path.join(dirname, name)
    return _load_script_code_by_fpath(fpath)

def load_script(name, vars = None, dirname = None, code = None):
    """加载脚本
    @param {string} name 插件的名词，和脚本目录(/data/scripts)的相对路径
    @param {dict} vars 全局变量，相当于脚本的globals变量
    @param {dirname} dirname 自定义脚本目录
    @param {code} 指定code运行，不加载文件
    """
    code = _load_script_code(name, dirname)
    return exec_python_code(name, code, 
        record_stdout = False, raise_err = True, vars = vars)

def load_script_meta(fpath):
    code = _load_script_code_by_fpath(fpath)
    meta = dict()

    for line in code.split("\n"):
        if not line.startswith("#"):
            continue
        line = line.lstrip("#\t ")
        if not line.startswith("@"):
            continue

        # 去掉注释部分
        meta_line  = line.split("#", 1)[0]
        # 拆分元数据
        meta_parts = meta_line.split()
        meta_key   = meta_parts[0]
        meta_value = meta_parts[1:]
        meta[meta_key] = meta_value
    return meta

def exec_command(command, confirmed = False):
    pass
