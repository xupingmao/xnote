# encoding:utf-8
"""Xnote 模块管理器
 - 加载并注册模块
"""
from __future__ import print_function
import os
import sys
import gc
import traceback
import time
import copy
import json
import inspect
import six

from threading import Thread, Timer

try:
    from queue import Queue
except ImportError:
    from Queue import Queue


import web
import xconfig
import xtemplate
import xtables
import xutils
import xauth

from util import textutil
from xutils import Storage

config = xconfig

def wrapped_handler(handler_clz):
    # Py2 自定义类不是type类型
    # if not isinstance(handler_clz, type):
    #     return handler_clz
    if not inspect.isclass(handler_clz):
        return handler_clz

    def wrap(result):
        if isinstance(result, list):
            return json.dumps(result)
        elif isinstance(result, dict):
            return json.dumps(result)
        return result

    class WrappedHandler:
        """ 默认的handler装饰器
        1. 装饰器相对于继承来说，性能略差一些，但是更加安全，父类的方法不会被子类所覆盖
        2. 为什么不用Python的装饰器语法
           1. 作为一个通用的封装，所有子类必须通过这层安全过滤
           2. 子类不用引入额外的模块
        """
        def __init__(self):
            self.target = handler_clz()

        def GET(self, *args):
            # if xconfig.OPEN_PROFILE:
            #     def profile_wrapper(*args):
            #         self.response = wrapper_result(self.target.GET(*args))
            #     profile.runctx("profile_wrapper(*args)", globals(), locals())
            #     return self.response
            # else:
            #     return wrapper_result(self.target.GET(*args))
            return wrap(self.target.GET(*args))
            

        def POST(self, *args):
            return wrap(self.target.POST(*args))

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
    import xtemplate
    raise web.notfound(xtemplate.render("notfound.html"))

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
    six.print_(time.strftime("%Y-%m-%d %H:%M:%S"), msg)

class ModelManager:
    """模块管理器
    
    启动时自动加载`handlers`目录下的处理器和定时任务
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

        self.vars = vars
        self.search_dict = {}
        self.task_dict = {}
        self.model_list = []
        self.black_list = ["__pycache__"]
        self.failed_mods = []
        self.debug = True
        self.report_loading = False
        self.task_manager = TaskManager(app)
        self.blacklist = ("handlers.experiment")
    
    def reload_module(self, name):
        try:
            if self.report_loading:
                log("del " + name)
            del sys.modules[name]
            __import__(name)
            if self.report_loading:
                log("reimport " + name)
        except Exception as e:
            pass
        finally:
            pass

    def reload(self):
        """重启所有的模块"""
        
        self.reload_module("xtemplate")
        self.reload_module("xauth")
        self.reload_module("xutils")
        self.reload_module("xtables")
        self.mapping     = []
        self.model_list  = []
        self.failed_mods = []
        self.load_model_dir(config.HANDLERS_DIR)
        
        self.mapping += self.basic_mapping
        self.mapping += self.last_mapping
        self.app.init_mapping(self.mapping)
        
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
        
    def load_model_dir(self, parent = config.HANDLERS_DIR):
        dirname = parent.replace(".", "/")
        for filename in os.listdir(dirname):
            try:
                filepath = os.path.join(dirname, filename)
                if os.path.isdir(filepath):
                    self.load_model_dir(parent + "." + filename)
                    continue
                name, ext = os.path.splitext(filename)
                if os.path.isfile(filepath) and ext == ".py":
                    modname = parent + "." + name
                    if modname in sys.modules:
                        if self.report_loading:
                            log("del %s" % modname)
                        del sys.modules[modname] # reload module
                    if modname.startswith(self.blacklist):
                        continue
                    # Py3: __import__(name, globals=None, locals=None, fromlist=(), level=0)
                    # Py2: __import__(name, globals={}, locals={}, fromlist=[], level=-1)
                    # fromlist不为空(任意真值*-*)可以得到子模块,比如__import__("os.path", fromlist=1)返回<module "ntpath" ...>
                    # 参考Python源码import.c即可
                    # <code>has_from = PyObject_IsTrue(fromlist);</code>实际上是个Bool值
                    # level=0表示绝对路径，-1是默认的
                    # mod = __import__(modname, fromlist=1, level=0)
                    # six的这种方式也不错
                    mod = six._import_module(modname)
                    # mod = self.get_mod(rootmod, modname)
                    self.load_model(mod, modname)
                    # self.load_task(mod, modname)
            except Exception as e:
                self.failed_mods.append([filepath, e])
                ex_type, ex, tb = sys.exc_info()
                log("Fail to load module '%s'" % filepath)
                log("Model traceback (most recent call last):")
                traceback.print_tb(tb)
                log(ex)

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
        # xurls拥有最高优先级
        elif hasattr(module, "handler"):
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
        self.mapping.append(wrapped_handler(handler))
        if self.report_loading:
            log("Load mapping (%s, %s)" % (url, handler))

    def run_task(self):
        self.task_manager.run_task()

    def load_tasks(self):
        self.task_manager.load_tasks()

    def get_task_list(self):
        return self.task_manager.get_task_list()


class TaskManager:
    """定时任务管理器，仿照crontab"""
    def __init__(self, app):
        self.task_list = []
        self.app = app

    def _match(self, current, pattern):
        return str(current) == pattern or pattern == "*" or pattern == "no-repeat"

    def match(self, task, tm=None):
        """是否符合运行条件"""
        if tm is None:
            tm = time.localtime()

        if self._match(tm.tm_wday, task.tm_wday) \
                and self._match(tm.tm_hour, task.tm_hour) \
                and self._match(tm.tm_min, task.tm_min):
            return True
        return False

    def run_task(self):
        """执行定时任务"""
        # worker_thread = WorkerThread()
        self.load_tasks()

        def request_url(url):
            quoted_url = xutils.quote_unicode(url)
            if quoted_url.startswith(("http://", "https://")):
                # 处理外部HTTP请求
                response = xutils.urlopen(quoted_url).read()
                log("Request %r success" % quoted_url)
                return response
            elif quoted_url.startswith("script://"):
                name = quoted_url[len("script://"):]
                return xutils.exec_script(name)
            cookie = xauth.get_admin_cookie()
            return self.app.request(url, headers=dict(COOKIE=cookie))

        def run():
            while True:
                # 获取分
                tm = time.localtime()
                need_reload = False
                
                for task in self.task_list:
                    if self.match(task, tm):
                        # worker_thread.add_task(task)
                        try:
                            # task()
                            log("run task [%s]" % task.url)
                            # Python3 中的_thread模块不被推荐使用
                            timer = Timer(0, request_url, args = (task.url,))
                            timer.start()
                            if task.tm_wday == "no-repeat":
                                # 一次性任务直接删除
                                # xtables.get_schedule_table().update(active=0, where=dict(id=task.id))
                                xtables.get_schedule_table().delete(where=dict(id=task.id))
                                need_reload = True
                        except Exception as e:
                            log("run task [%s] failed, %s" % (task.url, e))
                        finally:
                            pass
                if need_reload:
                    self.load_tasks()
                # 等待下一个分钟
                time.sleep(60 - tm.tm_sec % 60)
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
        schedule = xtables.get_schedule_table()
        tasks = schedule.select(order="url")
        self.task_list = list(tasks)
            
    def save_tasks(self):
        self.load_tasks()
        
    def get_task_list(self):
        return copy.deepcopy(self.task_list)


class TaskThread(Thread):
    """docstring for TaskThread"""
    def __init__(self, func, *args):
        super(TaskThread, self).__init__(name="Xnote Task Thread")
        # 守护线程，防止卡死
        self.setDaemon(True)
        self.func = func
        self.args = args
        
    def run(self):
        self.func(*self.args)

class WorkerThread(Thread):
    """docstring for WorkerThread"""
    def __init__(self):
        super(WorkerThread, self).__init__()
        self.setDaemon(True)
        self._task_queue = Queue()

    def run(self):
        while True:
            if len(self._task_queue) > 0:
                task = self._task_queue.get()
                try:
                    task()
                except Exception as e:
                    pass
            else:
                time.sleep(0.1)

    def add_task(self, task):
        self._task_queue.put(task)
        
_manager = None        
def init(app, vars, last_mapping=None):
    global _manager
    _manager = ModelManager(app, vars, last_mapping = last_mapping)
    return _manager
    
def instance():
    global _manager
    return _manager
    
def reload():
    _manager.reload()

def load_tasks():
    _manager.load_tasks()

def request(*args, **kw):
    global _manager
    # request参数如下
    # localpart='/', method='GET', data=None, host="0.0.0.0:8080", headers=None, https=False, **kw
    return _manager.app.request(*args, **kw)
