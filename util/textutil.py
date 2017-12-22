# encoding=utf-8

__doc__ = """Methods for text operation"""

import re
import random

"""Methods to check the text"""

ALPHA_NUM = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def text_contains(text, words):
    """
    >>> text_contains("abc is good", "abc")
    True
    >>> text_contains("you are right", "rig")
    True
    >>> text_contains("hello,world,yep", ["hello", "yep"])
    True
    """
    if isinstance(words, str):
        return words in text
    elif isinstance(words, list):
        for word in words:
            if word not in text:
                return False
        return True
    else:
        raise Exception("unsupported type")

def count_alpha(text):
    count = 0
    for c in text:
        if _isalpha(c):
            count += 1
    return count

def count_digit(text):
    count = 0
    for c in text:
        if _isdigit(c):
            count += 1
    return count

def _isalpha(c):
    return (c >='a' and c <='z') or (c >= 'A' and c <= 'Z')

def _isdigit(c):
    return (c>='0' and c<='9')

def _isalnum(c):
    return _isalpha(c) or _isdigit(c)

def _chk_list(text, func):
    for c in text:
        if not func(c):
            return False
    return True

def isalpha(text):
    return _chk_list(text, _isalpha)

def isalnum(text):
    return _chk_list(text, _isalnum)

def isdigit(text):
    return _chk_list(text, _isdigit)

def issubsetof(text, collection):
    pass

"""Methods to parse the text
   Built-in methods
   - split, rsplit, splitlines
   - strip, lstrip, rstrip
   - partition, rpartition
   - ljust, rjust, center
"""


def remove(self, target):
    """
    >>> remove("this is a bat", "bat")
    'this is a '
    """
    return self.replace(target, "")

def between(self, start, end):
    """Get the text between start end end
    >>> between("start words end", "start", "end")
    ' words '
    """
    p1 = self.find(start)
    if p1 < 0:
        return ""
    p2 = self.find(end, p1)
    if p2 < 0:
        return ""
    return self[p1+len(start):p2]

def after(self, start):
    """
    >>> after("this is good", "this")
    ' is good'
    """
    p1 = self.find(start)
    if p1 >= 0:
        return self[p1+len(start):]

def split_words(text):
    text = text.replace("\t", ' ')
    words = text.split(' ')
    while words.count('') > 0:
        words.remove('')
    return words

def find(text, key, show_line=False, ignore_case=True):
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
    if not isinstance(key, list):
        keys = [key]
    else:
        keys = key
    if ignore_case:
        for i in range(len(keys)):
            keys[i] = keys[i].lower()
    for line in text.split("\n"):
        if ignore_case:
            target = line.lower()
        else:
            target = line
        if contains(target, keys):
            if show_line:
                result.append("%04d:%s" % (lineno, line))
            else:
                result.append(line)
        lineno += 1
    return result


def replace(text, origin, dest, ignore_case = False, use_template = False):
    """
    >>> replace('abc is good', 'iS', 'is not', True)
    'abc is not good'
    >>> replace("this is a long story", "loNg", "-long-", True)
    'this is a -long- story'
    >>> replace("use Template", "template", '<k>?</k>', True, True)
    'use <k>Template</k>'
    """
    if not ignore_case:
        if use_template:
            dest = dest.replace("?", origin)
        return text.replace(origin, dest)
    else:
        start = 0
        origin = origin.lower()
        text_lower = text.lower()
        new_text = ""
        pos = 0
        while pos >= 0:
            pos = text_lower.find(origin, start)
            if pos >= 0:
                new_text += text[start:pos]
                if use_template:
                    dest = dest.replace("?", text[pos:pos+len(origin)])
                new_text += dest
                start = pos+len(origin)
            else:
                new_text += text[start:]
        return new_text

def like(text, pattern):
    """
    >>> like("hello,world", "hello*")
    True
    >>> like ("yes", "y?s")
    True
    >>> like("what", "n*")
    False
    """

    # TODO 处理`,`
    re_pattern = pattern.replace("?", ".?")
    re_pattern = re_pattern.replace("*", ".*?")
    m = re.match(re_pattern, text)
    if m:
        return True
    return False


def byte2str(buf):
    for encoding in ("utf-8", "gbk", "gb2312"):
        try:
            return buf.decode(encoding)
        except:
            pass

def edit_distance0(a, b, la, lb, cache=None, replace_step=1):
    # 典型的可以使用动态规划，为了可读性，依旧保持原来的递归求解结构
    # 对于这种纯粹的函数，提供装饰器或者在虚拟机进行优化更方便理解
    if cache[la][lb] >= 0:
        return cache[la][lb]
    if la == 0:
        ret = lb
    elif lb == 0:
        ret = la
    elif a[la-1] == b[lb-1]:
        ret = edit_distance0(a, b, la-1, lb-1, cache, replace_step)
    else:
        # a删除一个字符a[la-1]
        d1 = edit_distance0(a, b, la-1, lb, cache, replace_step) + 1
        # a插入一个字符b[lb-1]
        d2 = edit_distance0(a, b, la, lb-1, cache, replace_step) + 1
        # 替换最后一个字符
        d3 = edit_distance0(a, b, la-1, lb-1, cache, replace_step) + replace_step
        ret = min(d1, d2, d3)
    cache[la][lb]=ret
    return ret

def edit_distance(a,b,replace_step=1):
    """最小编辑距离算法"""
    cache = [[-1 for i in range(len(b)+1)] for i in range(len(a)+1)]
    return edit_distance0(a,b,len(a),len(b),cache,replace_step)


def random_string(length, chars=ALPHA_NUM):
    """生成随机字符串，默认是字母表+数字"""
    randint = random.randint
    max_int = len(chars)-1
    value = ''
    for i in range(length):
        value += chars[randint(0, max_int)]
    return value


