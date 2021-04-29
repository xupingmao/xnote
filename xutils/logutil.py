# encoding=utf-8
# @author xupingmao
# @since 2016/12/09
# @modified 2021/04/29 23:08:44
import logging
import time
import inspect
import os
from xutils import fsutil
from xutils.dateutil import format_time
from xutils.imports import u

def async_func_deco():
    """同步调用转化成异步调用的装饰器"""
    def deco(func):
        def handle(*args, **kw):
            import xmanager
            xmanager.put_task(func, *args, **kw)
        return handle
    return deco

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

class SimpleLogger:

    def __init__(self, metric):
        self.metric = metric

    def trace(message, cost=0):
        trace(self.metric, message, cost)

    def info(message, cost=0):
        info(self.metric, message, cost)

    def warn(message, cost=0):
        warn(self.metric, message, cost)

    def error(message, cost=0):
        error(self.metric, message, cost)

def get_logger(name):
    return SimpleLogger(name)

def get_log_path(level = "INFO"):
    import xconfig
    date_time = time.strftime("%Y-%m")
    dirname = os.path.join(xconfig.LOG_DIR, date_time)
    fsutil.makedirs(dirname)
    date_str = time.strftime("%Y-%m-%d")
    fname = "xnote.%s.%s.log" % (date_str, level)
    return os.path.join(dirname, fname)

def log(fmt, show_logger = False, print_std = True, fpath = None, *argv):
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

    if print_std:
        print(message)

    if fpath is None:
        fpath = get_log_path()

    log_async(fpath, message)

def _write_log_sync(level, metric, message, cost):
    import xauth
    fpath = get_log_path(level)
    user_name = xauth.current_name()
    if user_name is None:
        user_name = "-"
    full_message = "%s|%s|%s|%s|%sms|%s" % (format_time(), level, user_name, metric, cost, message)
    # print(full_message)
    # 同步写在SAE上面有巨大的性能损耗
    do_log_sync(fpath, full_message)

def _write_log(level, metric, message, cost):
    import xauth
    fpath = get_log_path(level)
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

def warn_sync(metric, message, cost = 0):
    _write_log_sync("WARN", metric, message, cost)

@async_func_deco()
def log_async(fpath, full_message):
    do_log_sync(fpath, full_message)

def do_log_sync(fpath, full_message):
    with open(fpath, "ab") as fp:
        fp.write((full_message+"\n").encode("utf-8"))

def log_init_deco(message):
    """日志装饰器"""
    def deco(func):
        def handle(*args, **kw):
            log(message + " starting ...")
            try:
                result = func(*args, **kw)
                log(message + " finished")
                return result
            except Exception as e:
                log(message + " failed")
                raise e
        return handle
    return deco


def timeit_deco(repeat=1, logfile=False, logargs=False, name="", logret=False):
    """简单的计时装饰器，可以指定执行次数"""
    from xutils import dbutil
    dbutil.register_table("log_timeit", "耗时统计日志")

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
                print("[timeit]", name, "cost time: ", int((t2-t1)*1000), "ms")
            return ret
        return handle
    return deco

def profile_deco():
    """Profile装饰器,打印信息到标准输出,不支持递归函数"""
    import xconfig
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

# 别名
timeit  = timeit_deco
profile = profile_deco


