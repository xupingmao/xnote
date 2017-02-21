# encoding=utf-8

import sys
import inspect

import web
import xtemplate

class DocInfo:

    def __init__(self, name):
        self.name = name
        mod = sys.modules[name]
        functions = []
        self.mod = mod
        self.functions = functions
        self.doc = mod.__doc__

        attr_dict = mod.__dict__
        for attr in attr_dict:
            value = attr_dict[attr]
            # 通过__module__判断是否时本模块的函数
            # isroutine判断是否是函数或者方法
            if inspect.isroutine(value):
                argspec = ''
                try:
                    signature = inspect.signature(value)
                except (ValueError, TypeError):
                    signature = None
                if signature:
                    argspec = str(signature)
                functions.append([attr + argspec, value.__doc__])
            # TODO 处理类的文档，参考pydoc

class handler(object):

    def GET(self):
        args = web.input()
        name = args.name

        doc_info = None
        if name is not None:
            doc_info = DocInfo(name)

        return xtemplate.render("system/doc.html", doc_info = doc_info)