# encoding:utf-8
"""Xnote 模块管理器
 - 加载并注册模块
"""
import os
import sys
import traceback
import time
import copy
import json
from threading import Thread, Timer
from queue import Queue

import web
import xconfig
import xtemplate
import xtables
import xutils

from util import textutil

from xutils import ConfigParser
from xutils import Storage

config = xconfig

def wrapped_handler(handler_clz):
    if not isinstance(handler_clz, type):
        return handler_clz

    def wrapper_result(result):
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
            return wrapper_result(self.target.GET(*args))
            

        def POST(self, *args):
            return wrapper_result(self.target.POST(*args))

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
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg)

class ModelManager:
    """模块管理器
    
    启动时自动加载`handlers`目录下的处理器和定时任务
    """

    def __init__(self, app, vars, mapping = None):
        self.app = app # webpy app
        if mapping is None:
            self.basic_mapping = [] # webpy mapping
            self.mapping = []
        else:
            self.basic_mapping = mapping
            self.mapping = copy.copy(mapping)
        self.vars = vars
        self.search_dict = {}
        self.task_dict = {}
        self.model_list = []
        self.black_list = ["__pycache__"]
        self.failed_mods = []
        self.debug = True
        self.report_loading = False
        self.task_manager = TaskManager(app)
    
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
        self.mapping = list()
        self.model_list = list()
        self.failed_mods = []
        self.load_model_dir(config.HANDLERS_DIR)
        
        import xtemplate
        self.mapping += self.basic_mapping
        self.app.init_mapping(self.mapping)
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
                    # Py3: __import__(name, globals=None, locals=None, fromlist=(), level=0)
                    # Py2: __import__(name, globals={}, locals={}, fromlist=[], level=-1)
                    # fromlist不为空(任意真值*-*)可以得到子模块,比如__import__("os.path", fromlist=1)返回<module "ntpath" ...>
                    # 参考Python源码import.c即可
                    # <code>has_from = PyObject_IsTrue(fromlist);</code>实际上是个Bool值
                    # level=0表示绝对路径，-1是默认的
                    mod = __import__(modname, fromlist=1, level=0)
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

    def load_model(self, module, name):
        if hasattr(module, "xurls"):
            xurls = module.xurls
            for i in range(0, len(xurls), 2):
                url = xurls[i]
                handler = xurls[i+1]
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

    def add_search_key(self, url, key):
        self.search_dict[key] = url

    def search(self, words):
        result = []
        for m in self.model_list:
            if textutil.contains(m.searchkey, words):
                result.append(Storage(name=m.name, url=m.url, description = m.description))
        return result

    def run_task(self):
        self.task_manager.run_task()

    def add_task(self, task, interval):
        self.task_manager.add_task(task, interval)

    def load_tasks(self):
        self.task_manager.load_tasks()

    def get_task_dict(self):
        return self.task_manager.get_task_dict()



class TaskManager:
    """任务管理器"""
    def __init__(self, app):
        self.task_dict = {}
        self.app = app


    def match(self, task, tm=None):
        """是否符合运行条件"""
        if tm is None:
            tm = time.localtime()
        if hasattr(task, "interval"):
            if task.interval < 0:
                return False
            """定时任务"""
            current = time.time()
            if not hasattr(task, "next_time"):
                task.next_time = current
            if current >= task.next_time:
                task.next_time = current + task.interval
                return True
            return False
        return str(task.second) == str(tm.tm_sec)

    def run_task(self):
        """执行定时任务"""
        # worker_thread = WorkerThread()
        self.load_tasks()

        def run():
            while True:
                # 获取分
                tm = time.localtime()
                
                for taskname in self.task_dict:
                    task = self.task_dict[taskname]
                    if self.match(task, tm):
                        # TODO 需要优化成异步执行
                        # worker_thread.add_task(task)
                        try:
                            # task()
                            log("run task [%s]" % task.url)
                            # self.app.request(task.url)
                            func = self.app.request
                            # Python3 中的_thread模块不被推荐使用
                            timer = Timer(0, func, args = (task.url,))
                            timer.start()
                        except Exception as e:
                            log("run task [%s] failed, %s" % (taskname, e))
                        finally:
                            pass
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
            self.task_dict[task.url] = task
            return True
        except Exception as e:
            print("Add task %s failed, %s" % (url, e))
            return False
        
    def load_tasks(self):
        schedule = xtables.get_schedule_table()
        tasks = schedule.select(order="ctime DESC")
        self.task_dict = {}
        for task in tasks:
            self._add_task(task)

        # users = {}
        # path = "config/tasks.ini"
        # if not os.path.exists(path):
        #     return users
        # cf = ConfigParser()
        # cf.read(path, encoding="utf-8")
        # for section in cf.sections():
        #     url = cf.get(section, "url")
        #     interval = cf.get(section, "interval")
        #     self._add_task(url, interval)
            
    def save_tasks(self):
        self.load_tasks()
        # schedule = xtables.get_schedule_table()
        # for name in self.task_dict:
        #     task = self.task_dict[name]
        #     rows = schedule.select(where=dict(url=task.url))
        #     if rows.first() is None:
        #         schedule.insert(url=task.url, interval=task.interval, ctime=xutils.format_time(), mtime=xutils.format_time())
        #     else:
        #         schedule.update(where="url=$url", vars=dict(url=task.url), interval=task.interval, mtime=xutils.format_time())


        """保存到配置文件"""
        # cf = ConfigParser()
        # for index, name in enumerate(sorted(self.task_dict)):
        #     task = self.task_dict[name]
        #     section = "task" + str(index)
        #     cf.add_section(section)
        #     cf.set(section, "url", task.url)
        #     cf.set(section, "interval", str(task.interval))
            
        # with open("config/tasks.ini", "w") as fp:
        #     cf.write(fp)
        
    def get_task_dict(self):
        return copy.deepcopy(self.task_dict)


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
def init(app, vars):
    global _manager
    _manager = ModelManager(app, vars)
    return _manager
    
def instance():
    global _manager
    return _manager
    
def reload():
    _manager.reload()

