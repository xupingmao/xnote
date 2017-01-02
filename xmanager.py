# encoding:utf-8
import config
import os
import sys
import traceback
import time

from util import textutil
from copy import copy
from BaseHandler import Storage, reload_template
from threading import Thread

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
        
class ModelManager:

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
        self.mapping = list()
        self.model_list = list()
        
        self.load_model_dir("model")
        
        self.mapping += self.basic_mapping
        reload_template()
        self.app.init_mapping(self.mapping)
        
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
        
    def load_model_dir(self, parent = "model"):
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
                        print("del %s" % modname)
                        del sys.modules[modname] # reload module
                    rootmod = __import__(modname)
                    mod = self.get_mod(rootmod, modname)
                    self.load_model(mod, modname)
                    self.load_task(mod, modname)
            except Exception as e:
                ex_type, ex, tb = sys.exc_info()
                print("Fail to load module '%s'" % filepath)
                print("Model traceback (most recent call last):")
                traceback.print_tb(tb)
                print(ex)

    def load_model(self, module, name):
        if hasattr(module, "handler"):
            handler = module.handler
            clz = name.replace(".", "_")
            self.vars[clz] = module.handler
            if hasattr(module.handler, "__url__"):
                url = module.handler.__url__
            elif hasattr(handler, "__xurl__"):
                url = handler.__xurl__
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
            if self.debug:
                print("Load mapping (%s, %s)" % (url, module.__name__))

    def load_task(self, module, name):
        if hasattr(module, "task"):
            task = module.task
            if hasattr(task, "__xtaskname__"):
                taskname = task.__xtaskname__
                self.task_dict[taskname] = task()
                print("Load task (%s,%s)" % (taskname, module.__name__))

    def get_mapping(self):
        return self.mapping

    def add_mapping(self, url, clzname):
        self.mapping.append(url)
        self.mapping.append(clzname)

    def add_search_key(self, url, key):
        self.search_dict[key] = url

    def search(self, words):
        result = []
        for m in self.model_list:
            if textutil.contains(m.searchkey, words):
                result.append(Storage(name=m.name, url=m.url, description = m.description))
        return result

    def run_task(self):
        def run():
            intervals = 0
            while True:
                # print("intervals=", intervals)
                # 避免被Python转成大数
                if intervals >= 1000000:
                    intervals = 0
                for taskname in self.task_dict:
                    task = self.task_dict[taskname]
                    if intervals % task.__xinterval__ == 0:
                        newthread = TaskThread(task)
                        newthread.start()
                time.sleep(1)
                intervals+=1
        thread = TaskThread(run)
        thread.start()


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