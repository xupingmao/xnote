# encoding=utf-8
# @author xupingmao
# @since
# @modified 2021/11/07 22:01:00
import xutils
import xtemplate
import sys
import inspect
import xauth
from xutils import textutil
from xutils import six

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

def list_modules():
    result = []
    for modname in sys.modules:
        module = sys.modules[modname]
        if module != None:
            mod = ModuleInfo(module, modname)
            result.append(mod)
        else:
            # Py2中出现这种情况
            six.print_("%s is None" % modname)
    return sorted(result)

class DocInfo:

    def __init__(self, name, doc, type="function"):
        self.name = name
        self.doc = doc
        self.type = type
        self.uuid = textutil.create_uuid()

class ErrorModule:

    """无法找到该模块"""

    def __init__(self, name):
        self.name = name
        self.__file__ = "文件不存在"


class ModInfo:

    def __init__(self, name):
        self.name = name
        if name not in sys.modules:
            mod = ErrorModule(name)
        else:
            mod = sys.modules[name]
        
        functions      = []
        self.mod       = mod
        self.functions = functions
        self.doc       = mod.__doc__
        self.file      = ""

        if hasattr(mod, "__file__"):
            self.file = mod.__file__
            # process with Py2
            if self.file.endswith(".pyc"):
                self.file = self.file[:-1]

        attr_dict = mod.__dict__
        for attr in sorted(attr_dict):
            if attr[0] == '_':
                # 跳过private方法
                continue
            value = attr_dict[attr]
            # 通过__module__判断是否时本模块的函数
            # isroutine判断是否是函数或者方法
            value_mod = inspect.getmodule(value)
            if value_mod != mod:
                # 跳过非本模块的方法
                continue
            if inspect.isroutine(value):
                functions.append(DocInfo(attr + getargspec(value), value.__doc__))
            elif inspect.isclass(value):
                do_class(functions, attr, value)
            # TODO 处理类的文档，参考pydoc

def getargspec(value):
    argspec = ''
    try:
        signature = inspect.signature(value)
    except (ValueError, TypeError, AttributeError):
        signature = None
    if signature:
        argspec = str(signature)
    return argspec

def do_class(functions, name, clz):
    doc = getattr(clz, "__doc__")
    if doc == None:
        doc = "None"
    functions.append(DocInfo(name, doc, "class"))
    for attr in clz.__dict__:
        value = clz.__dict__[attr]
        if inspect.isroutine(value):
            if attr[0] == "_" and value.__doc__ is None:
                continue
            functions.append(DocInfo(name+"."+attr+getargspec(value), value.__doc__, "method"))

class ModuleDetailHandler(object):

    @xauth.login_required("admin")
    def GET(self):
        name = xutils.get_argument_str("name")
        force = xutils.get_argument("force")

        if force == "true":
            __import__(name)

        doc_info = None
        if name is not None:
            doc_info = ModInfo(name)
        return xtemplate.render("system/page/module_detail.html", 
            show_aside = False,
            doc_info = doc_info)

class ModuleListHandler(object):
    
    @xauth.login_required("admin")
    def GET(self):
        return xtemplate.render("system/page/module_list.html", 
            show_aside = False,
            modules = list_modules(),
            sys = sys)

xurls = (
    r"/system/pydoc", ModuleListHandler,
    r"/system/modules_info", ModuleListHandler,
    r"/system/document", ModuleDetailHandler,
    r"/system/module_list", ModuleListHandler,
    r"/system/module_detail", ModuleDetailHandler
)
        