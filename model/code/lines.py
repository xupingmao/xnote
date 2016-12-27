import os
import web
import web.xtemplate as xtemplate
import xutils

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


def get_line_infos(path, recursive=False, type=None):
    line_infos = []

    ext_list = None
    if type is not None:
        ext_list = CODE_EXT_DICT.get(type)

    if ext_list is None:
        ext_list = CODE_EXT_LIST

    for root, dirs, files in os.walk(path):
        for fname in files:
            fpath = os.path.join(root, fname)
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
        args = web.input(path=None, recursive=None, type=None, count=None)

        path = args.path
        recursive = args.recursive
        type = args.type
        count = args.count
        typedict = CODE_EXT_DICT
        
        if count=="on":
            line_infos = get_line_infos(path, 
                recursive = recursive=="on", type = type)


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