# encoding=utf-8
# @author xupingmao
# @since 2017/02/19
# @modified 2018/11/25 19:58:24

"""代码分析工具，对文本文件进行全文搜索

    2018/09/23 - 支持正则表达式
    2017/03/26 - 支持查看命中行的上下文
    2017/02/19 - 第一版简单的搜索
"""
import re
import os
import xtemplate
import xutils
import xconfig
from xutils import textutil
from xutils import xhtml_escape, Storage


CODE_EXT_LIST = xconfig.FS_TEXT_EXT_LIST

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
    limit = int(limit/2)
    start = max(current - limit, 0)
    # start = max(current, 0)
    stop  = min(current + limit, len(lines))
    for i in range(start, stop):
        if i == current:
            around_lines.append(">>>>>>  %s" % lines[i])
        else:
            around_lines.append("  %04d  %s" % (i, lines[i]))
    return "\n".join(around_lines)

        
class LineInfo:
    """匹配行的信息"""
    around_lines_num = 20
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
        self.use_regexp = False

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

    def search_by_regexp(self, content, pattern, blacklist, ignore_case):
        result = []
        lineno = 1
        if pattern == "":
            return result

        lines = content.split("\n")
        for line in lines:
            m = pattern.match(line)
            if m:
                # line = str(m.groups())
                result.append(LineInfo(lineno, line, lines))
            lineno += 1
        return result

    def search_files(self, path, key, blacklist_str, filename, **kw):
        ignore_case = self.ignore_case
        recursive   = self.recursive
        total_lines = 0
        blacklist   = to_list(blacklist_str)

        if key is None or key == "":
            return [], total_lines
        if not os.path.isdir(path):
            raise Exception("%s is not a directory" % path)

        if self.use_regexp:
            pattern = re.compile(key)

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
                    xutils.print_exc()
                    result_list.append(Storage(name=fpath, 
                        result=[LineInfo(-1, "read file fail, e=%s" % e, None)]))
                    continue
                # 查找结果
                if self.use_regexp:
                    result = self.search_by_regexp(content, pattern, blacklist, ignore_case)
                else:
                    result = code_find(content, key, blacklist_str, 
                    ignore_case=ignore_case)
                if key != "" and len(result) == 0:
                    # key do not match
                    continue
                total_lines += len(result)
                result_list.append(Storage(name=fpath, result = result))

            if not recursive:
                break
        return result_list, total_lines


class handler:
    """analyze code"""
    def GET(self):
        ignore_case = xutils.get_argument("ignore_case", "off")
        recursive   = xutils.get_argument("recursive", "off")
        path        = xutils.get_argument("path", "", strip=True)
        key         = xutils.get_argument("key", "", strip=True)
        blacklist   = xutils.get_argument("blacklist", "", strip=True)
        filename    = xutils.get_argument("filename", "", strip=True)
        blacklist_dir = xutils.get_argument("blacklist_dir", "")
        regexp      = xutils.get_argument("regexp", "", strip=True)
        total_lines = 0
        error       = ""
        files       = []

        # print(path, blacklist, blacklist_dir, filename)
        searcher = FileSearch(path)
        searcher.set_exclude_dirs(blacklist_dir)
        if regexp == "on":
            searcher.use_regexp = True
        if ignore_case == "on":
            searcher.ignore_case = True
        if recursive == "on":
            searcher.recursive = True

        try:
            if path != "":
                files, total_lines = searcher.search_files(path, key, blacklist, filename);
        except Exception as e:
            error = e
        return xtemplate.render("code/code_search.html", 
            show_aside = False,
            files = files,
            total_lines = total_lines,
            path = path,
            ignore_case = ignore_case,
            error = error)

xurls = (
    r"/code/search", handler,
    r"/code/analyze", handler
)


