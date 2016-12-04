import config
import os
import sys
import traceback
from util import textutil
from copy import copy
from BaseHandler import Storage, reload_template

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
        self.model_list = []
        config.set("modelManager", self)

    def load_model_folder(self, mod, dirpath):
        """Load a folded model, like
         - file
            edit.html
            edit.py
            view.html
            view.py
        """
        dirname = os.path.basename(dirpath)
        for filename in os.listdir(dirpath):
            abspath = os.path.join(dirpath, filename)
            # do not allow directory here
            if os.path.isfile(abspath):
                name, ext = os.path.splitext(filename)
                if ext == ".py":
                    modname = mod + "." + dirname + "." + name
                    if modname in sys.modules:
                        print("del %s"%modname)
                        del sys.modules[modname]
                    try:
                        absmodule = __import__(modname)
                        parent = getattr(absmodule, dirname)
                        m = getattr(parent, name)
                        self.load_model(m, dirname + "/" + name)
                    except Exception as e:
                        ex_type, ex, tb = sys.exc_info()
                        print("Fail to load module '%s/%s'" % (dirpath, filename))
                        print("Model traceback (most recent call last):")
                        traceback.print_tb(tb)
                        print(ex)


    def load_model_dir(self):
        self.mapping = list()
        self.model_list = list()
        mod = "model"

        dirname = os.path.dirname(__file__)
        dirname = os.path.join(dirname, mod)
        for filename in os.listdir(dirname):
            try:
                filepath = os.path.join(dirname, filename)
                if os.path.isdir(filepath):
                    self.load_model_folder(mod, filepath)
                    continue
                name, ext = os.path.splitext(filename)
                if os.path.isfile(filepath) and ext == ".py":
                    modname = "model." + name
                    if modname in sys.modules:
                        print("del %s" % modname)
                        del sys.modules[modname] # reload module
                    parent = __import__(modname)
                    m = getattr(parent, name)
                    self.load_model(m, name)
            except Exception as e:
                ex_type, ex, tb = sys.exc_info()
                print("Fail to load module '%s'" % filename)
                print("Model traceback (most recent call last):")
                traceback.print_tb(tb)
                print(ex)

        self.mapping += self.basic_mapping
        print(self.mapping)
        reload_template()
        self.app.init_mapping(self.mapping)
        config.set("mapping", self.mapping)

    def load_model(self, m, name):
        if hasattr(m, "handler"):
            clz = '_h_' + name
            self.vars[clz] = m.handler
            url = "/" + name
            self.add_mapping(url, clz)
            if hasattr(m, "searchable"):
                if not m.searchable:
                    return
            wm = WebModel()
            wm.url = url
            if hasattr(m, "searchkey"):
                wm.searchkey = m.searchkey
            if hasattr(m, "name"):
                wm.name = m.name
            if hasattr(m, "description"):
                wm.description = m.description
            wm.init()
            self.model_list.append(wm)

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