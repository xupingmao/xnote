# encoding:utf-8
import config
import os
import sys
import traceback
import time
import copy

from util import textutil
from threading import Thread
from queue import Queue

from xutils import ConfigParser
from xutils import Storage
import xtemplate


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
        self.task_manager = TaskManager(app)
    
    def reload_module(self, name):
        try:
            print("del", name)
            del sys.modules[name]
            __import__(name)
            print("reimport", name)
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
        if len(self.failed_mods) == 0:
            return
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
            self.add_mapping(url, clz)
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

    def add_mapping(self, url, clzname):
        self.mapping.append(url)
        self.mapping.append(clzname)
        log("Load mapping (%s, %s)" % (url, clzname))

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

    def del_task(self, task):
        self.task_manager.del_task(task)

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
                            self.app.request(task.url)
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
        if url in self.task_dict:
            del self.task_dict[url]
            self.save_tasks()
            
    def _add_task(self, url, interval):
        try:
            interval = int(interval)
            self.task_dict[url] = Storage(url = url, interval = interval)
            return True
        except Exception as e:
            print("Add task %s failed, %s" % (url, e))
            return False
        
    def load_tasks(self):
        users = {}
        path = "config/tasks.ini"
        if not os.path.exists(path):
            return users
        cf = ConfigParser()
        cf.read(path, encoding="utf-8")
        for section in cf.sections():
            url = cf.get(section, "url")
            interval = cf.get(section, "interval")
            self._add_task(url, interval)
            
    def save_tasks(self):
        """保存到配置文件"""
        cf = ConfigParser()
        for index, name in enumerate(sorted(self.task_dict)):
            task = self.task_dict[name]
            section = "task" + str(index)
            cf.add_section(section)
            cf.set(section, "url", task.url)
            cf.set(section, "interval", str(task.interval))
            
        with open("config/tasks.ini", "w") as fp:
            cf.write(fp)
        
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
    
    