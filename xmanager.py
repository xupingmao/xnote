# encoding:utf-8
import config
import os
import sys
import traceback
import time

from util import textutil
from copy import copy
from threading import Thread
from queue import Queue

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

    def __init__(self, app, vars, mapping):
        self.app = app # webpy app
        self.basic_mapping = mapping # webpy mapping
        self.mapping = copy(mapping)
        self.vars = vars
        self.search_dict = {}
        self.task_dict = {}
        self.model_list = []
        self.black_list = ["__pycache__"]
        self.debug = True
    
    def reload(self):
        """重启所有的模块"""
        self.mapping = list()
        self.model_list = list()        
        self.load_model_dir(config.HANDLERS_DIR)
        
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
                    self.load_task(mod, modname)
            except Exception as e:
                ex_type, ex, tb = sys.exc_info()
                log("Fail to load module '%s'" % filepath)
                log("Model traceback (most recent call last):")
                traceback.print_tb(tb)
                log(ex)

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

        # worker_thread = WorkerThread()

        def run():
            intervals = 0
            while True:
                # print("intervals=", intervals)
                # 避免被Python转成大数
                if intervals >= 1000000:
                    intervals = 0
                for taskname in self.task_dict:
                    task = self.task_dict[taskname]
                    if intervals % task.interval == 0:
                        # TODO 需要优化成异步执行
                        # worker_thread.add_task(task)
                        try:
                            task()
                        except Exception as e:
                            print("run task [%s] failed, %s" % (taskname, e))
                time.sleep(1)
                intervals+=1
        chk_thread = TaskThread(run)
        chk_thread.start()


class TaskThread(Thread):
    """docstring for TaskThread"""
    def __init__(self, func, *args):
        super(TaskThread, self).__init__()
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