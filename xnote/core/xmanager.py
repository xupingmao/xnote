# encoding=utf-8
# @author xupingmao
# @since
# @modified 2022/04/03 22:09:50

"""Xnote 模块管理器
 * HandlerManager HTTP请求处理器加载和注册
 * CronTaskManager 定时任务注册和执行
 * EventManager 事件管理器
"""
from __future__ import print_function
import os
import sys
import re
import time
import copy
import inspect
import web
from xnote.core import xconfig, xauth, xnote_trace, xnote_hooks, xtemplate
import xutils
import threading
import logging
import xnote_migrate
from collections import deque
from threading import Thread
from xutils import Storage
from xutils import logutil
from xutils import tojson, MyStdout, cacheutil, u, dbutil, fsutil

__version__ = "1.0"
__author__ = "xupingmao (578749341@qq.com)"
__copyright__ = "(C) 2016-2021 xupingmao. GNU GPL 3."
__contributors__ = []

dbutil.register_table("schedule", "任务调度表 <schedule:id>")

TASK_POOL_SIZE = 500
LOCK = threading.RLock()
_event_logger = logutil.new_mem_logger("xmanager.event")
_async_logger = logutil.new_mem_logger("xmanager.async")
_debug_logger = logutil.new_mem_logger("xmanager.debug")
_error_logger = logutil.new_mem_logger("xmanager.error")

# 对外接口
_manager = None # type: HandlerManager
_event_manager = None # type: EventManager


class HandlerLocal:

    handle_class_dict = {}

    @property
    def handler_class(self):
        tid = id(threading.current_thread())
        return self.handle_class_dict.get(tid)
    
    @handler_class.setter
    def handler_class(self, value):
        tid = id(threading.current_thread())
        self.handle_class_dict[tid] = value

    @classmethod
    def get_handler_class_by_thread(cls, thread):
        tid = id(thread)
        return cls.handle_class_dict.get(tid)

handler_local = HandlerLocal()

def do_wrap_handler(pattern, handler_clz):
    # Python2中自定义类不是type类型
    # 这里只能处理类，不处理字符串
    if not inspect.isclass(handler_clz):
        return handler_clz

    def wrap_result(result, start_time=0.0):
        try:
            if isinstance(result, (list, dict)):
                web.header("Content-Type", "application/json")
                return tojson(result)
            return result
        finally:
            pass

    class WrappedHandler:
        """默认的handler装饰器
        1. 装饰器相对于继承来说，性能略差一些，但是更加安全，父类的方法不会被子类所覆盖
        2. 为什么不用Python的装饰器语法
           1. 作为一个通用的封装，所有子类必须通过这层安全过滤，而不是声明才过滤
           2. 子类不用引入额外的模块
        """
        # 使用浮点数是为了防止自动转大数
        visited_count = 0.0
        handler_class = handler_clz

        def __init__(self):
            self.target_class = handler_clz
            self.target = handler_clz()
            self.pattern = pattern

        def GET(self, *args):
            xnote_trace.start_trace()
            start_time = time.time()
            WrappedHandler.visited_count += 1.0
            handler_local.handler_class = self.target
            try:
                return wrap_result(self.target.GET(*args), start_time)
            finally:
                handler_local.handler_class = None

        def POST(self, *args):
            """常用于提交HTML FORM表单、新增资源等"""
            xnote_trace.start_trace()
            WrappedHandler.visited_count += 1.0
            handler_local.handler_class = self.target
            try:
                return wrap_result(self.target.POST(*args))
            finally:
                handler_local.handler_class = None

        def HEAD(self, *args):
            return wrap_result(self.target.HEAD(*args))

        def OPTIONS(self, *args):
            return wrap_result(self.target.OPTIONS(*args))

        def PROPFIND(self, *args):
            return wrap_result(self.target.PROPFIND(*args))

        def PROPPATCH(self, *args):
            return wrap_result(self.target.PROPPATCH(*args))

        def PUT(self, *args):
            """更新资源，带条件时是幂等方法"""
            return wrap_result(self.target.PUT(*args))

        def LOCK(self, *args):
            return wrap_result(self.target.LOCK(*args))

        def UNLOCK(self, *args):
            return wrap_result(self.target.UNLOCK(*args))

        def MKCOL(self, *args):
            return wrap_result(self.target.MKCOL(*args))

        def COPY(self, *args):
            return wrap_result(self.target.COPY(*args))

        def MOVE(self, *args):
            return wrap_result(self.target.MOVE(*args))

        def DELETE(self, *args):
            return wrap_result(self.target.DELETE(*args))

        def SEARCH(self, *args):
            return wrap_result(self.target.SEARCH(*args))

        def CONNECT(self, *args):
            """建立tunnel隧道"""
            return wrap_result(self.target.CONNECT(*args))

        def __getattr__(self, name):
            xutils.error("xmanager", "unknown method %s" % name)
            return getattr(self.target, name)

    return WrappedHandler


def notfound():
    """404请求处理器"""
    import xtemplate
    raise web.notfound(xtemplate.render(
        "common/page/notfound.html", show_aside=False))


class WebModel:
    def __init__(self):
        self.name = ""
        self.url = ""
        self.description = ""
        self.searchkey = ""

    def init(self):
        if self.name == "":
            self.name = self.searchkey
        if self.name == "":  # if still empty
            self.name = self.url
        self.searchkey = self.name + self.url + self.searchkey + self.description
        self.description = "[工具]" + self.description


def log(msg):
    # six.print_(time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    xutils.info("xmanager", msg)


def warn(msg):
    # six.print_(time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    xutils.warn("xmanager", msg)


def import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]

class HandlerManager:
    """模块管理器
    启动时自动加载`handlers`目录下的处理器以及定时任务
    """

    def __init__(self, app, vars, mapping=None, last_mapping=None):
        self.app = app  # webpy app
        if mapping is None:
            self.basic_mapping = []  # webpy mapping
            self.mapping = []
        else:
            self.basic_mapping = mapping
            self.mapping = copy.copy(mapping)

        if last_mapping is None:
            self.last_mapping = []
        else:
            self.last_mapping = last_mapping

        self.vars = vars
        self.search_dict = {}
        self.task_dict = {}
        self.model_list = []
        self.black_list = ["__pycache__"]
        self.failed_mods = []
        self.debug = True
        self.report_loading = False
        self.report_unload = True
        self.task_manager = CronTaskManager(app)

        # stdout装饰器，方便读取print内容
        if not isinstance(sys.stdout, MyStdout):
            sys.stdout = MyStdout(sys.stdout)

    def reload_module(self, name):
        try:
            if self.report_unload:
                log("del " + name)
            del sys.modules[name]
            __import__(name)
            if self.report_loading:
                log("reimport " + name)
        except Exception:
            xutils.print_exc()
        finally:
            pass

    def reload(self):
        """重启handlers目录下的所有的模块"""
        self.mapping = []
        self.model_list = []
        self.failed_mods = []

        xtemplate.reload()
        
        # 移除所有的事件处理器
        remove_event_handlers()

        # 重新加载HTTP处理器
        # 先全部卸载，然后全部加载，否则可能导致新的module依赖旧的module
        self.load_model_dir(dirname=xconfig.HANDLERS_DIR, unload=True, mod_name="handlers")
        self.load_model_dir(dirname=xconfig.HANDLERS_DIR, load=True, mod_name="handlers")

        # 重新加载定时任务
        self.load_tasks()

        for reload_func in xnote_hooks.get_reload_hooks():
            reload_func(self)

        self.mapping += self.basic_mapping
        self.mapping += self.last_mapping
        self.app.init_mapping(self.mapping)

        # set 404 page
        self.app.notfound = notfound

        load_init_script()
        fire("sys.reload")

    def get_mod(self, module, name):
        namelist = name.split(".")
        del namelist[0]
        mod = module
        for name in namelist:
            mod = getattr(mod, name)
        return mod

    def load_model_dir(self, unload=False, load=False, mod_name="handlers", dirname=""):
        dirname = os.path.abspath(dirname)
        if not os.path.exists(dirname):
            err_msg = f"model_dir not found: {dirname}"
            logging.error(err_msg)
            raise Exception(err_msg)
        
        for filename in os.listdir(dirname):
            filepath = os.path.join(dirname, filename)
            try:
                if os.path.isdir(filepath):
                    subdir = os.path.join(dirname, filepath)
                    self.load_model_dir(mod_name=mod_name+"."+filename, unload=unload, load=load, dirname=subdir)
                    continue
                name, ext = os.path.splitext(filename)
                if os.path.isfile(filepath) and ext == ".py":
                    modname = mod_name + "." + name
                    old_mod = sys.modules.get(modname)
                    if old_mod is not None:
                        if hasattr(old_mod, "unload"):
                            old_mod.unload()
                        if self.report_unload:
                            log("del %s" % modname)
                        if unload:
                            del sys.modules[modname]  # reload module
                    # Py3: __import__(name, globals=None, locals=None, fromlist=(), level=0)
                    # Py2: __import__(name, globals={}, locals={}, fromlist=[], level=-1)
                    # fromlist不为空(任意真值*-*)可以得到子模块,比如__import__("os.path", fromlist=1)返回<module "ntpath" ...>
                    # 参考Python源码import.c即可
                    # <code>has_from = PyObject_IsTrue(fromlist);</code>实际上是个Bool值
                    # level=0表示绝对路径，-1是默认的
                    # mod = __import__(modname, fromlist=1, level=0)
                    # six的这种方式也不错
                    if load:
                        mod = import_module(modname)
                        self.resolve_module(mod, modname)
            except Exception as e:
                self.failed_mods.append([filepath, e])
                _error_logger.log("Fail to load module %r" % filepath)
                _error_logger.log("Model traceback (most recent call last):")
                err_msg = xutils.print_exc()
                _error_logger.log(err_msg)
                # 严格校验模式，直接阻断启动
                raise e

        self.report_failed()

    def report_failed(self):
        for info in self.failed_mods:
            log("Failed info: %s" % info)

    def resolve_module(self, module, modname):
        modpath = "/".join(modname.split(".")[1:-1])
        if not modpath.startswith("/"):
            modpath = "/" + modpath
        if hasattr(module, "xurls"):
            xurls = module.xurls
            for i in range(0, len(xurls), 2):
                url = xurls[i]
                handler = xurls[i+1]
                if not url.startswith(modpath):
                    log("WARN: pattern %r is invalid, should starts with %r" %
                        (url, modpath))
                self.add_mapping(url, handler)
        # xurls拥有最高优先级，下面代码兼容旧逻辑
        elif hasattr(module, "handler"):
            self.resolve_module_old(module, modname)

    def get_url_old(self, name):
        namelist = name.split(".")
        del namelist[0]
        return "/" + "/".join(namelist)

    def resolve_module_old(self, module, modname):
        name = modname
        handler = module.handler
        clz = name.replace(".", "_")
        self.vars[clz] = module.handler

        if hasattr(module.handler, "__url__"):
            url = module.handler.__url__
        elif hasattr(handler, "__xurl__"):
            url = handler.__xurl__
        elif hasattr(handler, "xurl"):
            url = handler.xurl
        else:
            url = self.get_url_old(name)

        self.add_mapping(url, handler)

        if hasattr(module, "searchable"):
            if not module.searchable:
                return

        wm = WebModel()
        wm.url = url

        if hasattr(module, "searchkey"):
            wm.searchkey = module.searchkey
        if hasattr(module, "name"):
            wm.name = module.name
        if hasattr(module, "description"):
            wm.description = module.description
        wm.init()

        self.model_list.append(wm)

    def load_task(self, module, name):
        if not hasattr(module, "task"):
            return

        task = module.task
        if hasattr(task, "taskname"):
            taskname = task.taskname
            self.task_dict[taskname] = task()
            log("Load task (%s,%s)" % (taskname, module.__name__))

    def get_mapping(self):
        return self.mapping

    def add_mapping(self, url, handler):
        self.mapping.append(url)
        self.mapping.append(do_wrap_handler(url, handler))
        if self.report_loading:
            log("Load mapping (%s, %s)" % (url, handler))

    def start_cron_job(self):
        self.task_manager.start_cron_job()

    def load_tasks(self):
        self.task_manager.do_load_tasks()

    def get_task_list(self):
        return self.task_manager.get_task_list()


class CronTaskManager:
    """定时任务管理器，模拟crontab"""

    def __init__(self, app):
        self.task_list = []
        self.ext_task_list = [] # 扩展任务
        self.app = app
        self.thread_started = False

    def _match(self, current, pattern):
        if pattern == "mod5":
            return current % 5 == 0
        return str(current) == pattern or pattern == "*" or pattern == "no-repeat"

    def match(self, task, tm=None):
        """是否符合运行条件"""
        if tm is None:
            tm = time.localtime()

        if self._match(tm.tm_wday+1, task.tm_wday) \
                and self._match(tm.tm_hour, task.tm_hour) \
                and self._match(tm.tm_min, task.tm_min):
            return True
        return False
    
    def request_url(self, task):
        url = task.url
        if url is None:
            url = ""

        quoted_url = xutils.quote_unicode(url)
        if quoted_url.startswith(("http://", "https://")):
            # 处理外部HTTP请求
            response = xutils.urlopen(quoted_url).read()
            xutils.log("Request %r success" % quoted_url)
            return response
        elif url.startswith("script://"):
            name = url[len("script://"):]
            return xutils.exec_script(name, False)

        cookie = xauth.get_user_cookie("admin")
        url = url + "?content=" + xutils.quote_unicode(str(task.message))

        return self.app.request(url, headers=dict(COOKIE=cookie))

    def check_and_run(self, task, tm):
        if self.match(task, tm):
            put_task_async(self.request_url, task)
            try:
                xutils.trace("RunTask",  task.url)
                if task.tm_wday == "no-repeat":
                    # 一次性任务直接删除
                    dbutil.delete(task.id)
                    self.do_load_tasks()
            except Exception as e:
                xutils.log("run task [%s] failed, %s" % (task.url, e))


    def start_cron_job(self):
        """开始执行定时任务"""

        def fire_cron_events(tm):
            fire("cron.minute", tm)
            if tm.tm_min == 0:
                fire("cron.hour", tm)

        def run():
            while True:
                # 获取时间信息
                tm = time.localtime()

                # 定时任务
                for task in self.task_list:
                    self.check_and_run(task, tm)

                # cron.* 事件
                put_task_async(fire_cron_events, tm)
                tm = time.localtime()

                # 等待下一个分钟
                sleep_sec = 60 - tm.tm_sec % 60
                if sleep_sec > 0:
                    quick_sleep(sleep_sec)

        self.do_load_tasks()

        if not self.thread_started and xconfig.WebConfig.cron_enabled:
            # 任务队列处理线程，开启两个线程
            WorkerThread("WorkerThread-1").start()
            WorkerThread("WorkerThread-2").start()

            # 定时任务调度线程
            CronTaskThread(run).start()
            self.thread_started = True

    def del_task(self, url):
        self.do_load_tasks()

    def _add_task(self, task):
        url = task.url
        try:
            self.task_list.append(task)
            return True
        except Exception as e:
            print("Add task %s failed, %s" % (url, e))
            return False

    def do_load_tasks(self):
        self.task_list = []
        self.load_system_cron_task()
        tasks = dbutil.prefix_list("schedule")
        self.task_list += list(tasks)

    def load_system_cron_task(self):
        # 系统默认的任务
        task_config = xconfig.load_cron_config()
        for task in task_config:
            self.task_list.append(Storage(**task))
        
        for task in self.ext_task_list:
            self.task_list.append(Storage(**task))

    def save_tasks(self):
        self.do_load_tasks()

    def get_task_list(self):
        return copy.deepcopy(self.task_list)


class CronTaskThread(Thread):
    """检查定时任务触发条件线程"""

    def __init__(self, func, *args):
        super(CronTaskThread, self).__init__(name="CronTaskDispatcher")
        # 守护线程，防止卡死
        self.daemon = True
        self.func = func
        self.args = args

    def run(self):
        self.func(*self.args)


class SyncTaskThread(Thread):
    """同步的线程，文件同步的频率较高，单独开启一个线程"""

    def __init__(self, name="SyncTaskThread"):
        super(SyncTaskThread, self).__init__()
        self.name = name
        self.daemon = True

    def run(self):
        while True:
            fire("sync.step")
            sleep_seconds = xconfig.WebConfig.sync_interval_seconds
            quick_sleep(sleep_seconds)


class WorkerThread(Thread):
    """执行任务队列的线程，内部有一个队列，所有线程共享"""

    # deque是线程安全的
    _task_queue = deque()

    def __init__(self, name="WorkerThread"):
        super(WorkerThread, self).__init__()
        self.daemon = True
        self.name = name

    def run(self):
        while True:
            # queue.Queue默认是block模式
            # 但是deque没有block模式，popleft可能抛出IndexError异常
            try:
                if self._task_queue:
                    func, args, kw = self._task_queue.popleft()

                    _async_logger.log("qsize:(%d), execute:(%s)",
                                      len(self._task_queue), func)

                    func(*args, **kw)
                else:
                    time.sleep(0.01)
            except Exception as e:
                err = xutils.print_exc()
                _async_logger.log("exception: %s", err)

    @staticmethod
    def add_task(func, args, kw):
        _async_logger.log("add_task, key:(%s)", func)
        WorkerThread._task_queue.append([func, args, kw])


class EventHandler:
    """事件处理器,执行的时候不抛出异常"""

    def __init__(self, event_type, func, is_async=True, description=None):
        self.event_type = event_type
        self.key = None
        self.func = func
        self.is_async = is_async
        self.description = description
        self.profile = True

        func_name = get_func_abs_name(func)

        if self.description:
            self.key = "%s:%s" % (func_name, self.description)
        else:
            self.key = func_name

    def execute(self, ctx=None):
        _debug_logger.log("event:(%s) key:(%s), is_async:(%s)",
                          self.event_type, self.key, self.is_async)

        if self.is_async:
            # 异步执行
            put_task(self.func, ctx)
        else:
            # 同步执行
            try:
                start = 0.0
                if self.profile:
                    start = time.time()
                self.func(ctx)
                if self.profile:
                    cost_time = (time.time()-start)*1000
                    # xutils.trace("EventHandler", self.key, int((stop-start)*1000))
                    _event_logger.log(
                        "key:(%s), cost_time:(%.2fms)", self.key, cost_time)
            except:
                xutils.print_exc()

    def __eq__(self, other):
        if self.key is not None:
            return self.key == other.key
        return type(self) == type(other) and self.func == other.func

    def __str__(self):
        if self.is_async:
            return "<EventHandler %s async>" % self.key
        return "<EventHandler %s>" % self.key


class SearchHandler(EventHandler):

    pattern = re.compile(r".*")

    def execute(self, ctx=None):        
        try:
            matched = self.pattern.match(ctx.key)
            if not matched:
                return
            start = time.time()
            ctx.groups = matched.groups()
            self.func(ctx)
            stop = time.time()
            xutils.trace("SearchHandler", self.key, int((stop-start)*1000))
        except:
            xutils.print_exc()

    def __str__(self):
        pattern = u(self.pattern.pattern)
        return "<SearchHandler /%s/ %s>" % (pattern, self.key)


def get_func_abs_name(func):
    module = inspect.getmodule(func)
    if module is not None:
        return module.__name__ + "." + func.__name__
    else:
        func_globals = func.__globals__
        script_name = func_globals.get("script_name", "unknown")
        script_name = xutils.unquote(script_name)
        return script_name + "." + func.__name__


class EventManager:
    """事件管理器，每个事件由一个执行器链组成，执行器之间有一定的依赖性
    @since 2018/01/10
    """
    _handlers = dict()

    def add_handler(self, handler):
        """注册事件处理器
        事件处理器的去重,通过判断是不是同一个函数，不通过函数名，如果修改初始化脚本需要执行【重新加载模块】功能
        """
        event_type = handler.event_type
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            warn("handler %s is already registered" % handler)
            return
        # XXX 使用str(handler)在Python2.7环境下报错
        xutils.trace("EventRegister", "%s" % handler)
        handlers.append(handler)
        self._handlers[event_type] = handlers

    def fire(self, event_type, ctx=None):
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            handler.execute(ctx)

    def remove_handlers(self, event_type=None):
        """移除事件处理器"""
        if event_type is None:
            self._handlers = dict()
        else:
            self._handlers[event_type] = []


@xutils.log_init_deco("xmanager.init")
def init(app, vars, last_mapping=None):
    global _manager
    global _event_manager

    _event_manager = EventManager()
    _manager = HandlerManager(app, vars, last_mapping=last_mapping)

    # 初始化
    reload()

    # 启动任务
    _manager.start_cron_job()

    # 同步任务线程
    SyncTaskThread().start()

    # 数据库升级相关
    xnote_migrate.migrate()

    return _manager


def instance():
    global _manager
    return _manager


@xutils.log_init_deco("xmanager.reload")
def reload():    
    with LOCK:
        # 重载处理器
        get_handler_manager().reload()


def load_init_script():
    if xconfig.INIT_SCRIPT is not None and os.path.exists(xconfig.INIT_SCRIPT):
        try:
            xutils.exec_script(xconfig.INIT_SCRIPT)
        except:
            xutils.print_exc()
            print("Failed to execute script %s" % xconfig.INIT_SCRIPT)


def put_task(func, *args, **kw):
    """添加异步任务到队列，如果队列满了会自动降级成同步执行"""
    if len(WorkerThread._task_queue) > TASK_POOL_SIZE:
        # TODO 大部分是写日志的任务，日志任务单独加一个线程处理
        func_name = get_func_abs_name(func)
        xutils.warn_sync(
            "xmanager", "task deque is full func_name=%s" % func_name)
        try:
            func(*args, **kw)
        except Exception:
            xutils.print_exc()
    else:
        put_task_async(func, *args, **kw)


def put_task_async(func, *args, **kw):
    """添加异步任务到队列"""
    WorkerThread.add_task(func, args, kw)

def get_handler_manager():
    # type: () -> HandlerManager
    return _manager

def get_event_manager():
    # type: () -> EventManager
    return _event_manager

def load_tasks():
    get_handler_manager().load_tasks()


def get_task_list():
    return get_handler_manager().get_task_list()


def request(*args, **kw):
    global _manager
    # request参数如下
    # localpart='/', method='GET', data=None, host="0.0.0.0:8080", headers=None, https=False, **kw
    return get_handler_manager().app.request(*args, **kw)


def add_event_handler(handler):
    get_event_manager().add_handler(handler)


def remove_event_handlers(event_type=None):
    get_event_manager().remove_handlers(event_type)


def set_event_handlers0(event_type, handlers, is_async=True):
    manager = get_event_manager()
    manager.remove_handlers(event_type)
    for handler in handlers:
        manager.add_handler(event_type, handler, is_async)

def quick_sleep(seconds):
    """可以快速从睡眠中重启"""
    start_time = time.time()
    while True:
        time.sleep(0.1)
        wait_time = time.time() - start_time
        if wait_time > seconds:
            return
        if xconfig.EXIT_CODE == 205:
            return

def fire(event_type, ctx=None):
    """发布一个事件"""
    get_event_manager().fire(event_type, ctx)


def listen(event_type_list, is_async=True, description=None):
    """事件监听器注解"""

    # 同步任务使用专门的线程执行
    if event_type_list == "sync.step":
        is_async = False

    def deco(func):
        event_manager = get_event_manager()
        if isinstance(event_type_list, list):
            for event_type in event_type_list:
                handler = EventHandler(event_type, func,
                                       is_async=is_async,
                                       description=description)
                event_manager.add_handler(handler)
        else:
            event_type = event_type_list
            handler = EventHandler(event_type, func,
                                   is_async=is_async,
                                   description=description)
            event_manager.add_handler(handler)
        return func
    return deco


def searchable(pattern=r".*", description=None, event_type="search"):
    """搜索装饰器"""
    def deco(func):
        handler = SearchHandler(event_type, func, description=description)
        # unicode_pat = r"^%s\Z" % u(pattern)
        unicode_pat = u(pattern)
        handler.pattern = re.compile(unicode_pat)
        _event_manager.add_handler(handler)
        return func
    return deco


def find_plugins(category, orderby=None):
    return xutils.call("plugin.find_plugins", category, orderby=orderby)


@logutil.async_func_deco()
def add_visit_log(user_name, url):
    # type: (str, str) -> None
    return xutils.call("plugin.add_visit_log", user_name, url)


def restart():
    get_handler_manager().app.stop()
    xconfig.EXIT_CODE = 205
    sys.exit(205)
