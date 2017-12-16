# encoding=utf-8

import re

import xutils
from handlers.base import *
from xutils import xhtml_escape

CODE_EXT_LIST = (".java",  # Java
                 ".c",     # C语言
                 ".h",
                 ".cpp",   # C++
                 ".hpp",
                 ".vm",    # velocity
                 ".html",  # HTML
                 ".htm",
                 ".js",    
                 ".json", 
                 ".css", 
                 ".xml",   # XML
                 ".xsd",
                 ".csv",   # csv table
                 ".proto", # proto buf
                 ".py",    # Python
                 ".txt",   # Text
                 ".lua",   # Lua
                 ".rb",    # Ruby
                 ".go",    # Go
                 ".m",     # Objective-C, Matlab
                 ".conf",  # configuration
                 ".ini",
                 ".rc",
                 )

# TODO 对于小文件可以尝试当成文本文件来处理

def contains_all(self, words):
    """
    >>> contains_all("abc is good", ["abc"])
    True
    >>> contains_all("you are right", ["rig"])
    True
    >>> contains_all("hello,world,yep", ["hello", "yep"])
    True
    """
    if len(words) == 0:
        return False
    for word in words:
        if word not in self:
            return False
    return True

def contians_any(text, words):
    if len(words) == 0:
        return False

    for word in words:
        if word in text:
            return True
    return False

        
def to_list(key):
    """转换成list
    >>> to_list("1 2 3")
    ['1', '2', '3']
    >>> to_list("1  3 4")
    ['1', '3', '4']
    """
    if key == "" or key == None:
        return []
    if key[0] == '"' and key[-1] == '"':
        return [key[1:-1]]
    keys = key.split(" ")
    return list(filter(lambda x: x != "", keys))


def get_pretty_around_text(lines, current, limit):
    around_lines = []
    # start = max(current - limit, 0)
    start = max(current, 0)
    stop  = min(current + limit, len(lines))
    for i in range(start, stop):
        if i == current:
            around_lines.append(">>>>>>  %s" % lines[i])
        else:
            around_lines.append("  %04d  %s" % (i, lines[i]))
    return "\n".join(around_lines)

        
class LineInfo:
    """匹配行的信息"""
    around_lines_num = 100
    def __init__(self, lineno, text, lines=None):
        self.lineno = lineno
        self.text = text
        if lines:
            index = self.lineno-1
            num = self.around_lines_num
            # 负数会转成尾部索引
            begin = max(0, index-num)
            self.around_text = get_pretty_around_text(lines, index, self.around_lines_num)
            # self.around_text_prev = "\n    ".join(lines[index-num:index])
            # self.around_text_next = "\n    ".join(lines[index+1:index+num])
        else:
            self.around_text = ""
            self.around_text_prev = ""
            self.around_text_next = ""

    def __str__(self):
        return "%04d:%s" % (self.lineno, self.text)

def code_find(text, key, blacklist_str="", ignore_case=True):
    """ find key in text, return a list

    >>> find('hello,world', 'hello')
    ['0001:hello,world']

    >>> find('hell1,world\\nhello,kid', 'hello')
    ['0002:hello,kid']
    
    >>> find("yes", "")
    []
    """
    result = []
    lineno = 1
    if key == "":
        return result
    keys = to_list(key)
    blacklist = to_list(blacklist_str)

    if ignore_case:
        for i in range(len(keys)):
            keys[i] = keys[i].lower()
    lines = text.split("\n")
    for line in lines:
        if ignore_case:
            target = line.lower()
        else:
            target = line
        if contains_all(target, keys) and not contians_any(target, blacklist):
            result.append(LineInfo(lineno, line, lines))
        lineno += 1
    return result

class FileSearch:
    """文件搜索"""
    def __init__(self, path):
        self.path = path
        self.ignore_case = False
        self.recursive = False

    def set_exclude_dirs(self, blacklist_dir):
        path = self.path
        self.exclude_dirs = []
        if blacklist_dir != "":
            for item in blacklist_dir.split(","):
                item = item.strip()
                item = os.path.join(path, item)
                item = '^' + item.replace("*", ".*") + '$'
                print(item)
                self.exclude_dirs.append(re.compile(item))

    def should_skip(self, root, fname, filename):
        name, ext = os.path.splitext(fname)
        # 过滤黑名单
        if ext not in CODE_EXT_LIST:
            return True

        # 过滤Mac临时文件
        if fname.startswith("._"):
            return True

        fpath = os.path.join(root, fname)
        for pattern in self.exclude_dirs:
            if pattern.match(root):
                return True

        if filename != "" and not textutil.like(fname, filename):
            # filename do not match
            return True
        return False

    def search_files(self, path, key, blacklist_str, filename, **kw):
        ignore_case = self.ignore_case
        recursive = self.recursive

        if key is None or key == "":
            return []
        if not os.path.isdir(path):
            raise Exception("%s is not a directory" % path)
        result_list = []
        for root, dirs, files in os.walk(path):
            for fname in files:
                # 匹配文件名，过滤黑名单
                if self.should_skip(root, fname, filename):
                    # print("skip", fname)
                    continue
                try:
                    fpath = os.path.join(root, fname)
                    content = xutils.readfile(fpath)
                except Exception as e:
                    print("exception")
                    result_list.append(Storage(name=fpath, 
                        result=[LineInfo(-1, "read file fail, e=%s" % e, None)]))
                    continue
                # 查找结果
                result = code_find(content, key, blacklist_str, 
                    ignore_case=ignore_case)
                if key != "" and len(result) == 0:
                    # key do not match
                    continue
                result_list.append(Storage(name=fpath, result = result))

            if not recursive:
                break
        return result_list


class handler(BaseHandler):
    """analyze code"""
    def default_request(self):
        ignore_case = self.get_argument("ignore_case", "off")
        recursive   = self.get_argument("recursive", "off")
        path        = self.get_argument("path", "", strip=True)
        key         = self.get_argument("key", "", strip=True)
        blacklist   = self.get_argument("blacklist", "", strip=True)
        filename    = self.get_argument("filename", "", strip=True)
        blacklist_dir = self.get_argument("blacklist_dir", "")

        # print(path, blacklist, blacklist_dir, filename)
        file_search = FileSearch(path)
        file_search.set_exclude_dirs(blacklist_dir)
        if ignore_case == "on":
            file_search.ignore_case = True
        if recursive == "on":
            file_search.recursive = True

        error = ""
        files = []
        try:
            if path != "":
                files = file_search.search_files(path, key, blacklist, filename);
        except Exception as e:
            error = e
        finally:
            self.render(files = files,
                path = path,
                ignore_case = ignore_case,
                error = error)

searchkey = "code,代码分析工具"

name = "代码分析工具"
description = "对代码进行全文检索"