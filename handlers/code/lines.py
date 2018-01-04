# encoding=utf-8

import os
import web
import re
import xauth
import xtemplate
import xutils

from collections import OrderedDict

CODE_EXT_LIST = [
    ".c",    ".cpp", ".h",       # C 
    ".java", 
    ".js",   ".py",  ".lua", ".rb", ".php", # Scripts
    ".html", ".css", ".xml",         # xml/css
]

CODE_EXT_DICT = OrderedDict()
CODE_EXT_DICT["Python"]      = [".py"]
CODE_EXT_DICT["Python(web)"] = [".py", ".html"]
CODE_EXT_DICT["Java"]        = [".java"]
CODE_EXT_DICT["Web前端"]     = [".html", ".htm", ".js", ".css"]
CODE_EXT_DICT["C/C++"]       = [".c", ".h", ".cpp", ".hpp"]
CODE_EXT_DICT["Lua"]         = [".lua"]
CODE_EXT_DICT["Ruby"]        = [".rb"],
CODE_EXT_DICT["Php"]         = [".php"]

class LinesInfo(object):
    """docstring for LinesInfo"""
    def __init__(self, fname, lines = 0, comments = 0, blanklines = 0, root = None):
        super(LinesInfo, self).__init__()
        self.fname = fname
        self.lines = lines
        self.comments = comments
        self.blanklines = blanklines
        self.validlines = lines - blanklines
        self.display_name = fname
        if root:
            self.root = root
            self.display_name = xutils.get_relative_path(fname, root)

class LineCounter:

    def __init__(self):
        self.filter_text = ""
        self.lines_sort = False

    def count(self):
        pass

    def get_line_infos(self, path, recursive=False, type=None, skip_func = lambda fname: False):
        line_infos  = []
        filter_text = self.filter_text
        ext_list    = None

        if type is not None:
            ext_list = CODE_EXT_DICT.get(type)

        if ext_list is None:
            ext_list = CODE_EXT_LIST

        for root, dirs, files in os.walk(path):
            # if root.startswith(blacklist):
            #     # print(root,"is in blacklist")
            #     continue
            for fname in files:
                fpath = os.path.join(root, fname)
                relative_path = xutils.get_relative_path(fpath, path)
                if skip_func(relative_path):
                    continue
                _, ext = os.path.splitext(fname)
                if ext not in ext_list:
                    continue
                try:
                    text = xutils.readfile(fpath)
                    if len(text) == 0:
                        continue
                except:
                    line_infos.append(LinesInfo(fpath))
                    continue
                if filter_text not in text:
                    continue
                lines = text.count("\n") + 1  # 换行符数量+1，最后一行有效
                blanklines = 0
                for line in text.split("\n"):
                    line = line.strip()
                    if line == "":
                        blanklines+=1
                line_infos.append(LinesInfo(fpath, lines, 
                    blanklines = blanklines, root=path))
            if not recursive:
                break

        total_lines  = 0
        total_blanks = 0
        for info in line_infos:
            total_lines  += info.lines
            total_blanks += info.blanklines
        total = LinesInfo("Total", total_lines, 
            blanklines = total_blanks)
        total.fname = None

        line_infos.insert(0, total)
        if self.lines_sort:
            line_infos.sort(key = lambda info: -info.lines)
        else:
            line_infos.sort(key = lambda info: info.display_name)
        return line_infos


class handler:

    @xauth.login_required("admin")
    def GET(self):
        args = web.input(path=None, 
            recursive="off", 
            type=None, 
            count=None, 
            blacklist="")

        path      = args.path
        recursive = args.recursive
        type      = args.type
        count     = args.count
        typedict  = CODE_EXT_DICT
        blackliststr = args.blacklist
        filter_text  = xutils.get_argument("filter_text", "")
        blacklist    = re.split(r"[,\n]", blackliststr)
        lines_sort   = xutils.get_argument("lines_sort", "")
        # blacklist = tuple(map(lambda value: os.path.join(path, value.strip(' ')), blacklist))
        # print(blacklist)

        patterns = []
        for item in blacklist:
            item = item.strip()
            item = '^' + item.replace("*", ".*") + '$'
            patterns.append(re.compile(item))

        def skip_func(fpath):
            for p in patterns:
                if p.match(fpath):
                    return True
            return False
        
        if count=="on":
            counter = LineCounter()
            counter.lines_sort = (lines_sort == "on")
            counter.filter_text = filter_text
            line_infos = counter.get_line_infos(path, 
                recursive = recursive=="on", type = type, skip_func = skip_func)
        else:
            line_infos = []


        # return xtemplate.render("code/lines.html", **locals())
        return xtemplate.render("code/lines.html", 
            typedict = typedict,
            line_infos = line_infos,
            **args)
            
    @xauth.login_required("admin")
    def POST(self):
        args = web.input(_method="POST")
        path = args.path
        recursive = args.recursive
        type = args.type
        recursive = recursive == "on"

        if path is None:
            line_infos = []
        else:
            counter = LineCounter()
            line_infos = counter.get_line_infos(path, 
                recursive = recursive, type = type)
        
        typedict = CODE_EXT_DICT
        # return xtemplate.render("code/lines.html", **locals())
        return xtemplate.render("code/lines.html", 
            typedict = typedict,
            line_infos = line_infos,
            **args)