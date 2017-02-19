# encoding=utf-8
import sys
import xtemplate

class ModuleInfo:

    def __init__(self, mod, sysname):
        self.name = mod.__name__
        self.sysname = sysname
        self.is_builtin = False
        if hasattr(mod, "__file__"):
            self.file = mod.__file__
        else:
            self.file = "?"
        if hasattr(mod, "__spec__"):
            # self.is_builtin = mod.__spec__.origin
            pass
        self.info = str(mod)

    def __lt__(self, info):
        return self.sysname < info.sysname

def query_modules():
    modules = []
    for modname in sys.modules:
        module = sys.modules[modname]
        mod = ModuleInfo(module, modname)
        modules.append(mod)
    return sorted(modules)

class handler(object):
    
    def GET(self):
        return xtemplate.render("system/modules_info.html", 
            modules = query_modules(),
            sys = sys)
        