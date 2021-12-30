# encoding=utf-8
# @author xupingmao
# @since 2016/12/09
# @modified 2021/12/30 22:46:46
import logging
import time
import inspect
import os
import threading
import xutils
from collections import deque
from xutils import fsutil
from xutils.dateutil import format_time
from xutils.imports import u


class LogThread(threading.Thread):
    
    task_queue = deque()
    MAX_TASK_QUEUE = 1000

    def __init__(self, name="LogThread"):
        super(LogThread, self).__init__()
        self.setDaemon(True)
        self.setName(name)

    def put_task(self, func, *args, **kw):
        if len(self.task_queue) > self.MAX_TASK_QUEUE:
            print(format_time(), "Too many log task")
            func(*args, **kw)
        else:
            self.task_queue.append([func, args, kw])

    def run(self):
        while True:
            # queue.Queue默认是block模式
            # 但是deque没有block模式，popleft可能抛出IndexError异常
            try:
                if self.task_queue:
                    func, args, kw = self.task_queue.popleft()
                    func(*args, **kw)
                else:
                    time.sleep(0.01)
            except Exception as e:
                xutils.print_exc()

LOG_THREAD = LogThread()
LOG_THREAD.start()

def async_func_deco():
    """同步调用转化成异步调用的装饰器"""
    def deco(func):
        def handle(*args, **kw):
            LOG_THREAD.put_task(func, *args, **kw)
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
            log("%-30s ..." % message)
            try:
                result = func(*args, **kw)
                log("%-30s [OK]" % message)
                return result
            except Exception as e:
                log("%-30s [FAIL]" % message)
                raise e
        return handle
    return deco

def log_deco(message):
    """日志装饰器"""
    def deco(func):
        def handle(*args, **kw):
            try:
                result = func(*args, **kw)
                log(message + " [OK]")
                return result
            except Exception as e:
                log(message + " [FAIL]")
                raise e
        return handle
    return deco

def timeit_deco(repeat=1, logfile=False, logargs=False, name="", logret=False, switch_func=None):
    """简单的计时装饰器，可以指定执行次数"""
    from xutils import dbutil
    dbutil.register_table("log_timeit", "耗时统计日志")

    def deco(func):
        def handle(*args, **kw):
            if switch_func != None:
                need_log = switch_func()
            else:
                need_log = True

            if not need_log:
                return func(*args, **kw)

            t1 = time.time()
            for i in range(repeat):
                ret = func(*args, **kw)
            t2 = time.time()

            func_name = name

            if func_name == "":
                func_name = func.__name__

            msg_buf = []
            msg_buf.append(func_name)
            if logargs:
                msg_buf.append("args:" + str(args))
            if logret:
                msg_buf.append("result:" + str(ret))

            message = "|".join(msg_buf)

            if logfile:
                trace(message, int((t2-t1)*1000))
            else:
                print("[timeit]", message, "cost time: ", int((t2-t1)*1000), "ms")
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


