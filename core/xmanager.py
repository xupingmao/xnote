# encoding=utf-8
# @author xupingmao
# @since
# @modified 2020/01/27 11:06:34

"""Xnote 模块管理器
 * 请求处理器加载和注册
 * 定时任务注册和执行
 * 插件注册和查找
"""
from __future__ import print_function
import os
import sys
import gc
import re
import traceback
import time
import copy
import json
import profile
import inspect
import six
import web
import xconfig
import xtemplate
import xtables
import xutils
import xauth
import threading
from collections import deque
from threading import Thread, Timer, current_thread
from xutils import Storage, Queue, tojson, MyStdout, cacheutil, u, dbutil, fsutil

__version__      = "1.0"
__author__       = "xupingmao (578749341@qq.com)"
__copyright__    = "(C) 2016-2017 xupingmao. GNU GPL 3."
__contributors__ = []

def wrapped_handler(pattern, handler_clz):
    # Py2 自定义类不是type类型
    if not inspect.isclass(handler_clz):
        return handler_clz

    def wrap(result):
        if isinstance(result, (list, dict)):
            web.header("Content-Type", "application/json")
            return tojson(result)
        return result

    class WrappedHandler:
        """ 默认的handler装饰器
        1. 装饰器相对于继承来说，性能略差一些，但是更加安全，父类的方法不会被子类所覆盖
        2. 为什么不用Python的装饰器语法
           1. 作为一个通用的封装，所有子类必须通过这层安全过滤，而不是声明才过滤
           2. 子类不用引入额外的模块
        """
        # 防止自动转大数，浮点数不会转
        visited_count = 0.0
        handler_class = handler_clz

        def __init__(self):
            self.target_class = handler_clz
            self.target = handler_clz()
            self.pattern = pattern

        def GET(self, *args):
            WrappedHandler.visited_count += 1.0
            threading.current_thread().handler_class = self.target
            result = wrap(self.target.GET(*args))
            threading.current_thread().handler_class = None
            return result
            
        def POST(self, *args):
            WrappedHandler.visited_count += 1.0
            threading.current_thread().handler_class = self.target
            result = wrap(self.target.POST(*args))
            threading.current_thread().handler_class = None
            return result

        def search_priority(self):
            return 0

        def search_match(self, input):
            if hasattr(self.target, "search_match"):
                return self.search_match(input)
            return False

        def search(self, *args):
            """ 如果子类实现了搜索接口，通过该方法调用 """
            if hasattr(self.target, "search"):
                return self.search(*args)
            return None

    return WrappedHandler

def notfound():
    """404请求处理器"""
    import xtemplate
    raise web.notfound(xtemplate.render("notfound.html", show_aside = False))

class WebModel:
    def __init__(self):
        self.name = ""
        self.url = ""
        self.description = ""
        self.searchkey = ""

    def init(self):
        if self.name == "":
            self.name = self.searchkey
        if self.name == "": # if still empty
            self.name = self.url
        self.searchkey = self.name + self.url + self.searchkey + self.description
        self.description = "[工具]" + self.description
        

def log(msg):
    # six.print_(time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    xutils.info("INIT", msg)

def warn(msg):
    # six.print_(time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    xutils.warn("INIT", msg)

class ModelManager:
    """模块管理器
    启动时自动加载`handlers`目录下的处理器以及定时任务
    """

    def __init__(self, app, vars, mapping = None, last_mapping=None):
        self.app = app # webpy app
        if mapping is None:
            self.basic_mapping = [] # webpy mapping
            self.mapping = []
        else:
            self.basic_mapping = mapping
            self.mapping = copy.copy(mapping)

        if last_mapping is None:
            self.last_mapping = []
        else:
            self.last_mapping = last_mapping

        self.vars           = vars
        self.search_dict    = {}
        self.task_dict      = {}
        self.model_list     = []
        self.black_list     = ["__pycache__"]
        self.failed_mods    = []
        self.debug          = True
        self.report_loading = False
        self.report_unload  = True
        self.task_manager   = TaskManager(app)
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
        except Exception as e:
            xutils.print_exc()
        finally:
            pass

    def reload(self):
        """重启handlers目录下的所有的模块"""
        self.mapping     = []
        self.model_list  = []
        self.failed_mods = []
        # remove all event handlers
        remove_handlers()
        self.load_model_dir(xconfig.HANDLERS_DIR)
        
        self.mapping += self.basic_mapping
        self.mapping += self.last_mapping
        self.app.init_mapping(self.mapping)
        
        del sys.modules['xtemplate']
        import xtemplate
        xtemplate.reload()

        # set 404 page
        self.app.notfound = notfound
        
    def get_mod(self, module, name):
        namelist = name.split(".")
        del namelist[0]
        mod = module
        for name in namelist:
            mod = getattr(mod, name)
        return mod
        
    def get_url(self, name):
        namelist = name.split(".")
        del namelist[0]
        return "/" + "/".join(namelist)
        
    def load_model_dir(self, parent = xconfig.HANDLERS_DIR):
        dirname = parent.replace(".", "/")
        if not os.path.exists(dirname):
            return
        for filename in os.listdir(dirname):
            try:
                filepath = os.path.join(dirname, filename)
                if os.path.isdir(filepath):
                    self.load_model_dir(parent + "." + filename)
                    continue
                name, ext = os.path.splitext(filename)
                if os.path.isfile(filepath) and ext == ".py":
                    modname = parent + "." + name
                    old_mod = sys.modules.get(modname)
                    if old_mod is not None:
                        if hasattr(old_mod, "unload"):
                            old_mod.unload()
                        if self.report_unload:
                            log("del %s" % modname)
                        del sys.modules[modname] # reload module
                    # Py3: __import__(name, globals=None, locals=None, fromlist=(), level=0)
                    # Py2: __import__(name, globals={}, locals={}, fromlist=[], level=-1)
                    # fromlist不为空(任意真值*-*)可以得到子模块,比如__import__("os.path", fromlist=1)返回<module "ntpath" ...>
                    # 参考Python源码import.c即可
                    # <code>has_from = PyObject_IsTrue(fromlist);</code>实际上是个Bool值
                    # level=0表示绝对路径，-1是默认的
                    # mod = __import__(modname, fromlist=1, level=0)
                    # six的这种方式也不错
                    mod = six._import_module(modname)
                    self.load_model(mod, modname)
            except Exception as e:
                self.failed_mods.append([filepath, e])
                log("Fail to load module '%s'" % filepath)
                log("Model traceback (most recent call last):")
                xutils.print_exc()

        self.report_failed()

    def report_failed(self):
        for info in self.failed_mods:
            log("Failed info: %s" % info)

    def load_model(self, module, modname):
        name = modname
        modpath = "/".join(modname.split(".")[1:-1])
        if not modpath.startswith("/"):
            modpath = "/" + modpath
        if hasattr(module, "xurls"):
            xurls = module.xurls
            for i in range(0, len(xurls), 2):
                url = xurls[i]
                handler = xurls[i+1]
                if not url.startswith(modpath):
                    log("WARN: pattern %r is invalid, should starts with %r" % (url, modpath))
                self.add_mapping(url, handler)
        # xurls拥有最高优先级，下面代码兼容旧逻辑
        elif hasattr(module, "handler"):
            self.load_model_old(module, modname)

    def load_model_old(self, module, modname):
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
            url = self.get_url(name)
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
        if hasattr(module, "task"):
            task = module.task
            if hasattr(task, "taskname"):
                taskname = task.taskname
                self.task_dict[taskname] = task()
                log("Load task (%s,%s)" % (taskname, module.__name__))

    def get_mapping(self):
        return self.mapping

    def add_mapping(self, url, handler):
        self.mapping.append(url)
        self.mapping.append(wrapped_handler(url, handler))
        if self.report_loading:
            log("Load mapping (%s, %s)" % (url, handler))

    def run_task(self):
        self.task_manager.run_task()

    def load_tasks(self):
        self.task_manager.load_tasks()

    def get_task_list(self):
        return self.task_manager.get_task_list()


class TaskManager:
    """定时任务管理器，模拟crontab"""
    def __init__(self, app):
        self.task_list = []
        self.app = app

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

    def run_task(self):
        """执行定时任务"""
        def request_url(task):
            url = task.url
            if url is None: url = ""
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

        def check_and_run(task, tm):
            if self.match(task, tm):
                put_task(request_url, task)
                try:
                    xutils.trace("RunTask",  task.url)
                    if task.tm_wday == "no-repeat":
                        # 一次性任务直接删除
                        dbutil.delete(task.id)
                        self.load_tasks()
                except Exception as e:
                    xutils.log("run task [%s] failed, %s" % (task.url, e))

        def fire_cron_events(tm):
            fire("cron.minute", tm)
            if tm.tm_min == 0:
                fire("cron.hour", tm)

        def run():
            while True:
                # 获取时间信息
                tm = time.localtime()
                for task in self.task_list:
                    check_and_run(task, tm)
                # cron.* 事件
                put_task(fire_cron_events, tm)
                tm = time.localtime()
                # 等待下一个分钟
                sleep_sec = 60 - tm.tm_sec % 60
                if sleep_sec > 0:
                    time.sleep(sleep_sec)
        
        self.load_tasks()
        # 任务队列处理线程，开启两个线程
        WorkerThread("WorkerThread-1").start()
        WorkerThread("WorkerThread-2").start()

        chk_thread = TaskThread(run)
        chk_thread.start()
        
    def add_task(self, url, interval):
        if self._add_task(url, interval):
            self.save_tasks()

    def del_task(self, url):
        self.load_tasks()
            
    def _add_task(self, task):
        url = task.url
        try:
            self.task_list.append(task)
            return True
        except Exception as e:
            print("Add task %s failed, %s" % (url, e))
            return False
        
    def load_tasks(self):
        # schedule       = xtables.get_schedule_table()
        # tasks          = schedule.select(order="url")
        tasks = dbutil.prefix_list("schedule")
        self.task_list = list(tasks)
        # 系统默认的任务
        backup_task = xutils.Storage(name="[系统]备份", url="/system/backup", 
            tm_wday = "*", tm_hour="11", tm_min="0", 
            message = "", sound=0, webpage=0, id=None)

        clean_task  = xutils.Storage(name = "[系统]磁盘清理", url="/cron/diskclean",
            tm_wday = "*", tm_hour="*", tm_min="0",
            message = "", sound=0, webpage=0, id=None)

        self.task_list.append(backup_task)
        self.task_list.append(clean_task)

    def save_tasks(self):
        self.load_tasks()
        
    def get_task_list(self):
        return copy.deepcopy(self.task_list)


class TaskThread(Thread):
    """检查定时任务触发条件线程"""
    def __init__(self, func, *args):
        super(TaskThread, self).__init__(name="TaskDispatcher")
        # 守护线程，防止卡死
        self.setDaemon(True)
        self.func = func
        self.args = args
        
    def run(self):
        self.func(*self.args)

class WorkerThread(Thread):
    """执行任务队列的线程，内部有一个队列，所有线程共享
    """
    
    _task_queue = deque()
    
    def __init__(self, name="WorkerThread"):
        super(WorkerThread, self).__init__()
        self.setDaemon(True)
        self.setName(name)

    def run(self):
        while True:
            # queue.Queue默认是block模式
            # 但是deque没有block模式，popleft可能抛出IndexError异常
            try:
                if self._task_queue:
                    func, args, kw = self._task_queue.popleft()
                    func(*args, **kw)
                else:
                    time.sleep(0.01)
            except Exception as e:
                xutils.print_exc()

class EventHandler:

    def __init__(self, event_type, func, is_async = False, description = ''):
        self.event_type  = event_type
        self.key         = None
        self.func        = func
        self.is_async    = is_async
        self.description = description
        self.profile     = True

        func_name = get_func_abs_name(func)

        if self.description:
            self.key = "%s:%s" % (func_name, self.description)
        else:
            self.key = func_name

    def execute(self, ctx=None):
        if self.is_async:
            put_task(self.func, ctx)
        else:
            try:
                if self.profile:
                    start = time.time()
                self.func(ctx)
                if self.profile:
                    stop  = time.time()
                    xutils.trace("EventHandler", self.key, int((stop-start)*1000))
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
        return "<string>." + func.__name__

    # filepath = inspect.getfile(func)
    # filename = os.path.basename(filepath)
    # basename, ext = os.path.splitext(filename)
    # return basename + "." + func.__name__

class EventManager:
    """事件管理器，每个事件由一个执行器链组成，执行器之间有一定的依赖性
    @since 2018/01/10
    """
    _handlers = dict()

    def add_handler(self, handler):
        """
        注册事件处理器
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

    def remove_handlers(self, event_type = None):
        """移除事件处理器"""
        if event_type is None:
            self._handlers = dict()
        else:
            self._handlers[event_type] = []

# 对外接口
_manager       = None
_event_manager = None
def init(app, vars, last_mapping = None):
    global _manager
    global _event_manager
    _event_manager = EventManager()
    _manager       = ModelManager(app, vars, last_mapping = last_mapping)
    return _manager

def instance():
    global _manager
    return _manager
    
def reload():
    _event_manager.remove_handlers()
    xauth.refresh_users()
    _manager.reload()
    # 重新加载定时任务
    _manager.load_tasks()

    cacheutil.clear_temp()
    load_init_script()
    load_plugins(xconfig.PLUGINS_DIR)
    fire("sys.reload")

def load_init_script():
    if xconfig.INIT_SCRIPT is not None:
        try:
            xutils.exec_script(xconfig.INIT_SCRIPT)
        except:
            xutils.print_exc()
            print("Failed to execute script %s" % xconfig.INIT_SCRIPT)

class PluginContext:

    def __init__(self):
        self.title = ""
        self.description = ""
        self.fname = ""

    # sort方法重写__lt__即可
    def __lt__(self, other):
        return self.title < other.title

    # 兼容Python2
    def __cmp__(self, other):
        return cmp(self.title, other.title)

def is_plugin_file(fpath):
    return os.path.isfile(fpath) and fpath.endswith(".py")

def load_plugin_file(fpath, fname = None):
    if fname is None:
        fname = os.path.basename(fpath)
    dirname = os.path.dirname(fpath)

    # plugin name
    pname = fsutil.get_relative_path(fpath, xconfig.PLUGINS_DIR)

    vars = dict()
    vars["script_name"] = pname
    vars["fpath"] = fpath
    try:
        module = xutils.load_script(fname, vars, dirname = dirname)
        main_class = vars.get("Main")
        if main_class != None:
            main_class.fname = fname
            main_class.fpath = fpath
            instance = main_class()
            context = PluginContext()
            context.fname = fname
            context.fpath = fpath
            context.name = os.path.splitext(fname)[0]
            context.title = getattr(instance, "title", "")
            context.category = xutils.attrget(instance, "category")
            context.url = "/plugins/%s" % pname
            if hasattr(main_class, 'on_init'):
                instance.on_init(context)
            context.clazz = main_class
            xconfig.PLUGINS_DICT[pname] = context
    except:
        xutils.print_exc()

def load_sub_plugins(dirname):
    for fname in os.listdir(dirname):
        fpath = os.path.join(dirname, fname)
        if is_plugin_file(fpath):
            # 支持插件子目录
            load_plugin_file(fpath, fname)

def load_plugins(dirname):
    if not xconfig.LOAD_PLUGINS_ON_INIT:
        return
    xconfig.PLUGINS_DICT = {}
    for fname in os.listdir(dirname):
        fpath = os.path.join(dirname, fname)
        if os.path.isdir(fpath):
            load_sub_plugins(fpath)
        if is_plugin_file(fpath):
            load_plugin_file(fpath, fname)

@xutils.timeit(logfile=True, logargs=True, name="FindPlugins")
def find_plugins(category):
    role = xauth.get_current_role()
    plugins = []

    if role is None:
        # not logged in
        return plugins

    if category == "None":
        category = None

    for fname in xconfig.PLUGINS_DICT:
        p = xconfig.PLUGINS_DICT.get(fname)
        if p and xutils.attrget(p.clazz, "category") == category:
            required_role = xutils.attrget(p.clazz, "required_role")
            if role == "admin" or required_role is None or required_role == role:
                plugins.append(p)
    plugins.sort()
    return plugins

def list_plugins(category):
    return 

def put_task(func, *args, **kw):
    """添加异步任务到队列"""
    WorkerThread._task_queue.append([func, args, kw])


def load_tasks():
    _manager.load_tasks()


def get_task_list():
    return _manager.get_task_list()


def request(*args, **kw):
    global _manager
    # request参数如下
    # localpart='/', method='GET', data=None, host="0.0.0.0:8080", headers=None, https=False, **kw
    return _manager.app.request(*args, **kw)


def add_handler(handler):
    _event_manager.add_handler(handler)


def remove_handlers(event_type=None):
    _event_manager.remove_handlers(event_type)


def set_handlers0(event_type, handlers, is_async=False):
    _event_manager.remove_handlers(event_type)
    for handler in handlers:
        _event_manager.add_handler(event_type, handler, is_async)


def fire(event_type, ctx=None):
    """发布一个事件"""
    _event_manager.fire(event_type, ctx)


def listen(event_type_list, is_async = False, description = None):
    """事件监听器注解"""
    def deco(func):
        if isinstance(event_type_list, list):
            for event_type in event_type_list:
                handler = EventHandler(event_type, func, 
                    is_async = is_async, 
                    description = description)
                _event_manager.add_handler(handler)
        else:
            event_type = event_type_list
            handler = EventHandler(event_type, func, 
                is_async = is_async, 
                description = description)
            _event_manager.add_handler(handler)
        return func
    return deco


def searchable(pattern = r".*", description = None, event_type = "search"):
    """搜索装饰器"""
    def deco(func):
        handler = SearchHandler(event_type, func, description = description)
        # unicode_pat = r"^%s\Z" % u(pattern)
        unicode_pat = u(pattern)
        handler.pattern = re.compile(unicode_pat)
        _event_manager.add_handler(handler)
        return func
    return deco


