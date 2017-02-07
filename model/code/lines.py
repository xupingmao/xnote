import os
import web
import xtemplate
import xutils
import re

CODE_EXT_LIST = [
    ".c", ".cpp", ".h",
    ".java", ".xml",
    ".js", ".py", ".lua", ".rb",
    ".html", ".css"
]

CODE_EXT_DICT = {
    "Python": [".py"],
    "web": [".html", ".htm", ".js", ".css"],
    "C/C++": [".c", ".h", ".cpp", ".hpp"],
    "Lua": [".lua"],
    "Ruby": [".rb"],
    "Java": [".java"],
}

class LinesInfo(object):
    """docstring for LinesInfo"""
    def __init__(self, fname, lines = 0, comments = 0, blanklines = 0):
        super(LinesInfo, self).__init__()
        self.fname = fname
        self.lines = lines
        self.comments = comments
        self.blanklines = blanklines
        self.validlines = lines - blanklines


def get_line_infos(path, recursive=False, type=None, skip_func = lambda fname: False):
    line_infos = []

    ext_list = None
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
            if skip_func(fpath):
                continue
            _, ext = os.path.splitext(fname)
            if ext not in ext_list:
                continue
            try:
                text = xutils.readfile(fpath)
            except:
                line_infos.append(LinesInfo(fpath))
                continue
            lines = text.count("\n")
            blanklines = 0
            for line in text.split("\n"):
                line = line.strip()
                if line == "":
                    blanklines+=1
            line_infos.append(LinesInfo(fpath, lines, 
                blanklines = blanklines))
        if not recursive:
            break

    total_lines = 0
    total_blanks = 0
    for info in line_infos:
        total_lines += info.lines
        total_blanks += info.blanklines
    total = LinesInfo("Total", total_lines, 
        blanklines = total_blanks)

    line_infos.insert(0, total)
    line_infos.sort(key = lambda info: -info.lines)
    return line_infos


class handler:

    def GET(self):
        args = web.input(path=None, recursive=None, type=None, count=None, blacklist="")

        path = args.path
        recursive = args.recursive
        type = args.type
        count = args.count
        typedict = CODE_EXT_DICT
        blackliststr = args.blacklist

        blacklist = blackliststr.split(",")
        # blacklist = tuple(map(lambda value: os.path.join(path, value.strip(' ')), blacklist))
        # print(blacklist)

        patterns = []
        for item in blacklist:
            item = item.strip()
            item = os.path.join(path, item)
            item = '^' + item.replace("*", ".*") + '$'
            patterns.append(re.compile(item))

        print(patterns)

        def skip_func(fpath):
            for p in patterns:
                if p.match(fpath):
                    return True
            return False
        
        if count=="on":
            line_infos = get_line_infos(path, 
                recursive = recursive=="on", type = type, skip_func = skip_func)
        else:
            line_infos = []


        # return xtemplate.render("code/lines.html", **locals())
        return xtemplate.render("code/lines.html", 
            typedict = typedict,
            line_infos = line_infos,
            **args)
            
    def POST(self):
        args = web.input(_method="POST")

        path = args.path
        recursive = args.recursive
        type = args.type

        if path is None:
            line_infos = []
        else:
            line_infos = get_line_infos(path, 
                recursive = recursive=="on", type = type)
        
        typedict = CODE_EXT_DICT
        # return xtemplate.render("code/lines.html", **locals())
        return xtemplate.render("code/lines.html", 
            typedict = typedict,
            line_infos = line_infos,
            **args)