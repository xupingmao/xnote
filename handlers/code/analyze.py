# encoding=utf-8

from handlers.base import *
from xutils import xhtml_escape

CODE_EXT_LIST = (".java", 
                 ".c",
                 ".h",
                 ".cpp",
                 ".hpp",
                 ".vm",
                 ".html",
                 ".xml",
                 ".js",
                 ".py",
                 ".json",
                 ".text",
                 ".xsd",
                 ".proto",
                 ".lua",
                 ".rb",
                 ".csv")
def contains(self, words):
    """
    >>> contains("abc is good", ["abc"])
    True
    >>> contains("you are right", ["rig"])
    True
    >>> contains("hello,world,yep", ["hello", "yep"])
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
    keys = key.split(" ")
    return list(filter(lambda x: x != "", keys))
        
def code_find(text, key, blacklist_str, show_line=False, ignore_case=True):
    """ find key in text, return a list

    >>> find('hello,world', 'hello')
    ['hello,world']

    >>> find('hell1,world\\nhello,kid', 'hello', True)
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
    for line in text.split("\n"):
        if ignore_case:
            target = line.lower()
        else:
            target = line
        if contains(target, keys) and not contians_any(target, blacklist):
            if show_line:
                result.append("%04d:%s" % (lineno, line))
            else:
                result.append(line)
        lineno += 1
    return result


class handler(BaseHandler):
    """analyze code"""

    def search_files(self, path, key, blacklist_str, filename, 
            ignore_case = False, recursive = True):
        if key is None or key == "":
            return []
        if not os.path.isdir(path):
            raise Exception("%s is not a directory" % path)
        result_list = []
        for root, dirs, files in os.walk(path):
            for fname in files:
                name, ext = os.path.splitext(fname)
                if ext not in CODE_EXT_LIST:
                    continue
                if fname.startswith("._"):
                    # pass mac os temp files
                    continue
                fpath = os.path.join(root, fname)
                if filename != "" and not textutil.like(fname, filename):
                    # filename do not match
                    continue
                try:
                    content = fsutil.readfile(fpath)
                except Exception as e:
                    result_list.append(Storage(name=fpath, result=["read file fail, e=%s" % e]))
                result = code_find(content, key, blacklist_str, 
                    show_line = True, ignore_case=ignore_case)
                if key != "" and len(result) == 0:
                    # key do not match
                    continue
                result_list.append(Storage(name=fpath, result = result))

            if not recursive:
                break
        return result_list

    def default_request(self):
        ignore_case = self.get_argument("ignore_case", "")
        recursive   = self.get_argument("recursive", "")
        path = self.get_argument("path", "")
        key  = self.get_argument("key", "")
        blacklist = self.get_argument("blacklist", "")
        filename = self.get_argument("filename", "")
        error = ""
        files = []
        try:
            if path != "":
                path = path.strip()
                key  = key.strip()
                blacklist = blacklist.strip()
                filename = filename.strip()
                files = self.search_files(path, key, blacklist, filename, 
                    ignore_case = ignore_case == "on", 
                    recursive = recursive == "on");
        except Exception as e:
            error = e
        finally:
            self.render(files = files,
                path = path,
                ignore_case = ignore_case)

searchkey = "code,代码分析工具"

name = "代码分析工具"
description = "对代码进行全文检索"