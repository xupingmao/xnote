# encoding=utf-8

import sys
import web
import web.xtemplate as xtemplate

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
            if hasattr(value, "__call__"):
                functions.append([attr, value.__doc__])

class handler(object):

    def GET(self):
        args = web.input()
        name = args.name

        doc_info = None
        if name is not None:
            doc_info = DocInfo(name)

        return xtemplate.render("system/doc.html", doc_info = doc_info)