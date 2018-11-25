# encoding=utf-8
# @author xupingmao
# @since
# @modified 2018/11/25 20:22:07
import six
import xutils
import xtemplate
import sys

class ModuleInfo:
    def __init__(self, mod, sysname):
        try:
            self.name = mod.__name__
        except:
            # getattr判断无效
            xutils.print_exc()
            self.name = "Unknown"
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
    for modname in sys.modules.copy():
        module = sys.modules[modname]
        if module != None:
            mod = ModuleInfo(module, modname)
            modules.append(mod)
        else:
            # Py2中出现这种情况
            six.print_("%s is None" % modname)
    return sorted(modules)

class handler(object):
    
    def GET(self):
        return xtemplate.render("system/modules_info.html", 
            show_aside = False,
            modules = query_modules(),
            sys = sys)

xurls = (
    r"/system/pydoc", handler,
    r"/system/modules_info", handler
)
        