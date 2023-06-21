# encoding=utf-8
# @author xupingmao
# @since 2016/12/09
# @modified 2022/04/16 08:53:48
import logging
import time
import inspect
import os
import threading
import json
from collections import deque

try:
    import cProfile as pf
except ImportError:
    import profile as pf

# 非标准库
import xutils
from xutils import fsutil
from xutils.imports import u


_write_log_lock = threading.RLock()

def _format_time():
    ct = time.time()
    msecs = (ct - int(ct)) * 1000

    st = time.localtime(ct)
    tf_base = time.strftime('%Y-%m-%d %H:%M:%S', st)
    return "%s,%03d" % (tf_base, msecs)

class TaskPool:
    def __init__(self, max_task_queue = 200):
        self.MAX_TASK_QUEUE = max_task_queue
        self.task_queue = deque()

    def put_task(self, func, *args, **kw):
        if len(self.task_queue) > self.MAX_TASK_QUEUE:
            print(_format_time(), "Too many log task, queue_size:", len(self.task_queue))
            func(*args, **kw)
        else:
            self.task_queue.append([func, args, kw])
        
    def popleft(self):
        return self.task_queue.popleft()
    
    def size(self):
        return len(self.task_queue)

    def print_task_queue(self):
        for item in self.task_queue:
            print(item)


empty_pool = TaskPool(0)

class AsyncThreadBase(threading.Thread):
    
    def __init__(self, name="AsyncThread", task_pool = empty_pool):
        super(AsyncThreadBase, self).__init__()
        self.daemon = True
        self.name = name
        self.task_pool = task_pool

    def run(self):
        while True:
            # queue.Queue默认是block模式
            # 但是deque没有block模式，popleft可能抛出IndexError异常
            try:
                if self.task_pool.size() > 0:
                    func, args, kw = self.task_pool.popleft()
                    func(*args, **kw)
                else:
                    time.sleep(0.01)
            except Exception as e:
                xutils.print_exc()
    
    def wait_task_done(self):
        while self.task_pool.size() > 0:
            func, args, kw = self.task_pool.popleft()
            func(*args, **kw)

class LogThread(AsyncThreadBase):
    def __init__(self, name="LogThread"):
        super().__init__(name)

class AsyncThread(AsyncThreadBase):
    pass

default_pool = TaskPool(200)

def init_async_pool(pool_size = 200, thread_size = 5):
    global default_pool
    default_pool = TaskPool(pool_size)

    for i in range(thread_size):
        suffix = str(i+1)
        thread = AsyncThread(name = "AsyncThread-" + suffix, task_pool=default_pool)
        thread.start()

def wait_task_done():
    while default_pool.size() > 0:
        time.sleep(0.1) # 等待任务完成

def async_func_deco():
    """同步调用转化成异步调用的装饰器"""
    def deco(func):
        def handle(*args, **kw):
            global default_pool
            default_pool.put_task(func, *args, **kw)
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

    def trace(self, message, cost=0):
        trace(self.metric, message, cost)

    def info(self, message, cost=0):
        info(self.metric, message, cost)

    def warn(self, message, cost=0):
        warn(self.metric, message, cost)

    def error(self, message, cost=0):
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
        message = "%s|%s.%s:%s %s" % (_format_time(), f_modname, f_name, f_lineno, message)
    else:
        message = "%s|%s" % (_format_time(), message)

    if print_std:
        print(message)

    if fpath is None:
        fpath = get_log_path()

    log_async(fpath, message)

def log_simple(fmt, *args):
    return log(fmt, False, True, None, *args)


def _write_log_sync(level, metric, message, cost):
    import xauth
    fpath = get_log_path(level)
    user_name = xauth.current_name()
    if user_name is None:
        user_name = "-"
    full_message = "%s|%s|%s|%s|%sms|%s" % (_format_time(), level, user_name, metric, cost, message)
    # print(full_message)
    # 同步写在SAE上面有巨大的性能损耗
    do_log_sync(fpath, full_message)

def _write_log(level, metric, message, cost):
    import xauth
    fpath = get_log_path(level)
    user_name = xauth.current_name()
    if user_name is None:
        user_name = "-"
    full_message = "%s|%s|%s|%s|%sms|%s" % (_format_time(), level, user_name, metric, cost, message)
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
    # 写日志文件要加锁防止冲突
    with _write_log_lock:
        # TODO 使用缓存优化日志
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

def log_deco(message, log_args = False, args_convert_func = None):
    """日志装饰器"""
    def deco(func):
        def handle(*args, **kw):
            args_str = ""
            if log_args:
                if args_convert_func != None:
                    args_str = args_convert_func(*args, **kw)
                else:
                    args_str = json.dumps(dict(args = args, kw = kw))

            start_time = time.time()
            try:
                result = func(*args, **kw)
                cost_time = (time.time() - start_time) * 1000
                log_simple("{}|{}|{}|{:.2f}ms", message, args_str, "success", cost_time)
                return result
            except Exception as e:
                cost_time = (time.time() - start_time) * 1000
                log_simple("{}|{}|{}|{:.2f}ms", message, args_str, "exception", cost_time)
                raise e
        return handle
    return deco

def timeit_deco(repeat=1, logfile=False, logargs=False, name="", logret=False, switch_func=None):
    """简单的计时装饰器，可以指定执行次数"""
    def deco(func):
        def handle(*args, **kw):
            if switch_func != None:
                need_log = switch_func()
            else:
                need_log = True

            if not need_log:
                return func(*args, **kw)

            t1 = time.time()
            ret = None
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
                logging.info("[timeit] %s, cost time: %s ms", message, int((t2-t1)*1000))
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


def get_mem_logger(*args, **kw): # type: (...) -> MemLogger
    return MemLogger.get_logger(*args, **kw)

def new_mem_logger(*args, **kw): # type: (...) -> MemLogger
    return MemLogger.get_logger(*args, **kw)

class MemLogger:

    _instances = set()
    _lock = threading.RLock()

    def __init__(self, name, size = 200, ttl = 60*60):
        self.name = name
        self.size = size
        self.data = deque()
        self.ttl = ttl
        self.st = time.time() # start_time
        MemLogger._instances.add(self)
        MemLogger.clear_expired()

    def __del__(self):
        MemLogger._instances.remove(self)

    @classmethod
    def clear_expired(cls):
        for logger in cls._instances:
            if logger.is_expired():
                del logger
    
    @classmethod
    def list_loggers(cls):
        loggers = [item for item in cls._instances]
        loggers.sort(key = lambda x:x.name)
        return loggers
    
    @classmethod
    def get_logger(cls, name, size = 200, ttl = 60*60):
        """根据名称获取logger"""
        with cls._lock:
            for logger in cls._instances:
                if logger.name == name:
                    return logger

        return MemLogger(name, size, ttl)

    def is_expired(self):
        if self.ttl < 0:
            return False
        return time.time() > (self.st+self.ttl)

    def log(self, message, *args):
        MemLogger.clear_expired()

        f_back    = inspect.currentframe().f_back
        f_code    = f_back.f_code
        f_modname = f_back.f_globals.get("__name__")
        func_name    = f_code.co_name
        func_lineno  = f_back.f_lineno

        head = "%s|%s:%s" % (_format_time(), func_name, func_lineno)
        if len(args) > 0:
            body = message % args
        else:
            body = message

        line = "%s|%s" % (head, body)

        self.data.append(line)
        if len(self.data) > self.size:
            self.data.popleft()
    
    info = log


    def text(self):
        return "\n".join(self.data)