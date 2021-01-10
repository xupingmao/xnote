# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2017/?/?
# @modified 2021/01/10 18:24:40
import re
import random
import json
import inspect
from xutils.imports import is_str, ConfigParser

try:
    from urllib.parse import quote, unquote
except ImportError:
    from urllib import quote, unquote

__doc__ = """文本处理函数库

Text Process Library
"""

ALPHA_NUM = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BLANK_CHAR_SET = set(" \n\t\r")

def contains_all(text, words):
    """
        >>> contains_all("abc is good", "abc")
        True
        >>> contains_all("you are right", "rig")
        True
        >>> contains_all("hello,world,yep", ["hello", "yep"])
        True
    """
    if is_str(words):
        return words in text
    elif isinstance(words, list):
        for word in words:
            if word not in text:
                return False
        return True
    else:
        raise TypeError("unsupported type")

text_contains = contains_all

def contains_any(text, words):
    if is_str(words):
        return words in text
    elif isinstance(words, (list, tuple)):
        for word in words:
            if word in text:
                return True
        return False
    else:
        raise TypeError("unsupported type, words require str, list, tuple")

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
    """
        >>> isalpha('a')
        True
        >>> isalpha('abc')
        True
        >>> isalpha('12abc')
        False
    """
    return _chk_list(text, _isalpha)

def isalnum(text):
    """
        >>> isalnum('123abc')
        True
        >>> isalnum('-abc-')
        False
    """
    return _chk_list(text, _isalnum)

def isdigit(text):
    """
        >>> isdigit('123')
        True
        >>> isdigit('abc111')
        False
    """
    return _chk_list(text, _isdigit)

def isblank(text):
    for c in text:
        if c not in BLANK_CHAR_SET:
            return False
    return True

def issubsetof(text, collection):
    pass

def is_cjk(c):
    """是否是CJK(中日韩统一表意文字)
    说明来自维基百科 https://zh.wikipedia.org/wiki/CJK
    @param {char} c 单个字符
    """
    code = ord(c)
    if 0x4E00 <= code and code <= 0x9FFF:
        # 1993年5月，正式制订最初的中日韩统一表意文字，位于U+4E00–U+9FFF这个区域，共20,902个字。
        return True
    if 0x3400 <= code and code <= 0x4DFF:
        # 1999年，依据ISO/IEC 10646的第17个修正案（Amendment 17）订定扩展区A，于U+3400–U+4DFF加入6,582个字。
        return True
    if 0x20000 <= code and code <= 0x2A6FF:
        # 2001年，依据ISO/IEC 10646-2，新增扩展区B，包含42,711个汉字。位于U+20000–U+2A6FF。
        return True
    if 0x9FA6 <= code and code <= 0x0FBB:
        # 2005年，依据ISO/IEC 10646:2003的第1个修正案（Amendment 1），基本多文种平面增加U+9FA6-U+9FBB，共22个汉字。
        return True
    if 0x2A700 <= code and code <= 0x2B734:
        # 2009年，统一码5.2扩展区C增加U+2A700–U+2B734
        return True
    if 0x9FC4 <= code and code <= 0x9FCB:
        # 2009年，统一码5.2基本多文种平面增加U+9FC4–U+9FCB。
        return True
    return False

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

def replace_between(self, start, end, target):
    p1 = self.find(start)
    if p1 < 0:
        return None
    p2 = self.find(end, p1)
    if p2 < 0:
        return None
    return self[:p1 + len(start)] + target + self[p2:]

def after(self, start):
    """
        >>> after("this is good", "this")
        ' is good'
    """
    p1 = self.find(start)
    if p1 >= 0:
        return self[p1+len(start):]

def split_chars(text):
    chars = []
    for c in text:
        if c.isprintable() and c not in BLANK_CHAR_SET:
            chars.append(c)
    return chars

def split_first(text, sep = ' '):
    """
        >>> split_first("find a.name b.name")
        ('find', 'a.name b.name')
        >>> split_first("find")
        ('find', '')
        >>> split_first('find-a.name b.name', '-')
        ('find', 'a.name b.name')
    """
    index = text.find(sep)
    if index >= 0:
        return text[:index], text[index+1:]
    return text, ""

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
        if contains_all(target, keys):
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
        start      = 0
        origin     = origin.lower()
        text_lower = text.lower()
        new_text   = ""
        pos        = 0
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

def edit_distance0(a, b, la, lb, cache=None, replace_step=2):
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

def edit_distance(a,b,replace_step=2):
    """最小编辑距离算法(Leven-shtein Distance)

        >>> edit_distance('ab', 'a')
        1
        >>> edit_distance('abc', 'ac')
        1
    """
    cache = [[-1 for i in range(len(b)+1)] for i in range(len(a)+1)]
    return edit_distance0(a,b,len(a),len(b),cache,replace_step)

def jaccard_similarity(str1, str2):
    """Jaccard/Tanimoto系数"""
    set1 = set(str1)
    set2 = set(str2)
    return float(len(set1.intersection(set2))) / len(set1.union(set2))

def jaccard_distance(str1, str2):
    return 1.0 - jaccard_similarity(str1, str2)

def random_string(length, chars=ALPHA_NUM):
    """生成随机字符串，默认是字母表+数字"""
    randint = random.randint
    max_int = len(chars)-1
    value = ''
    for i in range(length):
        value += chars[randint(0, max_int)]
    return value


def parse_config_text(text, ret_type = 'list'):
    """解析key/value格式的配置文本
    @param {string} text 配置文本内容
    @param {string} ret_type 返回的格式，包含list, dict
    """
    if ret_type == 'dict':
        config = dict()
    else:
        config = []
    for line in text.split("\n"): 
        line = line.strip()
        if line.find("#")!=-1: 
            # 删除注释部分
            line=line[0:line.find('#')]
        eq_pos = line.find('=')
        if eq_pos > 0: 
            key   = line[:eq_pos].strip()
            value = line[eq_pos+1:].strip()
            if ret_type == 'dict':
                config[key] = value
            else:
                config.append(dict(key=key, value=value))
    return config

def parse_ini_text(text):
    """解析INI文件内容"""
    data = dict()
    cf = ConfigParser()
    cf.read_string(text)
    names = cf.sections()
    for name in names:
        item = dict()
        options = cf.options(name)
        for option in options:
            value = cf.get(name, option)
            item[option] = value
        data[name] = item
    return data

def parse_simple_command(text):
    """
        >>> parse_simple_command("find a.name b.name")
        ('find', 'a.name b.name')
        >>> parse_simple_command("find")
        ('find', '')
        >>> parse_simple_command('find    a.name b.name')
        ('find', 'a.name b.name')
        >>> parse_simple_command('find-name \t lalala')
        ('find-name', 'lalala')
    """
    pattern = re.compile(r"^([^\s]+)\s+(.*)$")
    match = pattern.match(text)
    if match: return match.group(1, 2)
    return text, ""

def short_text(text, length):
    """
        >>> short_text('abc', 5)
        'abc'
        >>> short_text('abcdefg', 5)
        'abcdefg'
        >>> short_text('abcd', 5)
        'abcd'
        >>> short_text('中文12345678', 5)
        '中文1234..'
    """
    if len(text) <= length:
        return text
    pos = 0
    size = 0
    need_cut = False
    last_size = 1
    for c in text:
        pos += 1
        if ord(c) <= 127:
            # 半角
            size += 0.5
            last_size = 1
        else:
            size += 1
            last_size = 2
        if size == length:
            # 刚好
            if pos == len(text):
                # 最后一个字符
                return text
            if last_size == 2:
                # 上一个全角
                pos -= 1
            if last_size == 1:
                # 上一个半角
                pos -= 2
            need_cut = True
            break
        if size - length == 0.5:
            # 多一个半角，上一个字符一定是全角
            pos -= 2
            need_cut = True
            break
    if not need_cut:
        return text
    return text[:pos] + ".."

shortfor       = short_text
get_short_text = short_text

def get_camel_case(name, upper = False):
    """
        >>> get_camel_case('name')
        'name'
        >>> get_camel_case('get_name')
        'getName'
        >>> get_camel_case('get_my_name', True)
        'GetMyName'
    """
    target = ''
    for c in name:
        if upper:
            target += c.upper()
            upper = False
        elif c == '_':
            upper = True
        else:
            target += c
    return target
to_camel_case = get_camel_case

def get_underscore(name):
    """
        >>> get_underscore('getName')
        'get_name'
        >>> get_underscore('GetName')
        'get_name'
    """
    target = ''
    for index, c in enumerate(name):
        if c.isupper() and index != 0:
            target += '_' + c.lower()
        else:
            target += c.lower()
    return target
to_underscore = get_underscore

def generate_uuid():
    import uuid
    return uuid.uuid4().hex

def _encode_json(obj):
    """基本类型不会拦截"""
    if inspect.isfunction(obj):
        return "<function>"
    elif inspect.isclass(obj):
        return "<class>"
    elif inspect.ismodule(obj):
        return "<module>"
    return str(obj)

def tojson(obj, format=False):
    if format:
        return json.dumps(obj, sort_keys=True, default=_encode_json, indent=2)
    else:
        return json.dumps(obj, default=_encode_json)



def set_doctype(type):
    print("#!%s\n" % type)

def get_doctype(text):
    if text.startswith("#!html"):
        return "html"
    return "text"


def is_img_file(filename):
    """根据文件后缀判断是否是图片"""
    import os
    import xconfig
    name, ext = os.path.splitext(filename)
    return ext.lower() in xconfig.FS_IMG_EXT_LIST

def mark_text(content):
    import xconfig
    from xutils.marked_text_parser import TextParser, set_img_file_ext
    # 设置图片文集后缀
    set_img_file_ext(xconfig.FS_IMG_EXT_LIST)

    parser = TextParser()
    tokens = parser.parse(content)
    return "".join(tokens)

def mark_text_old(content):
    """简单的处理HTML"""
    # \xad (Soft hyphen), 用来处理断句的
    content = content.replace(u'\xad', '\n')
    lines = []
    # markdown的LINK样式
    for line in content.split("\n"):
        tokens = line.split()
        for index, item in enumerate(tokens):
            if item == "":
                continue
            elif item.startswith(("https://", "http://")):
                tokens[index] = '<a target="_blank" href="%s">%s</a>' % (item, item)
            elif item.startswith("file://"):
                href = item[7:]
                if is_img_file(href):
                    tokens[index] = '<img class="chat-msg-img x-photo" alt="%s" src="%s">' % (href, href)
                else:
                    name = href[href.rfind("/")+1:]
                    # 尝试urldecode名称
                    name = unquote(name)
                    tokens[index] = '<a href="%s">%s</a>' % (href, name)
            elif item.count("#") >=1:
                tokens[index] = re.sub(r"#([^#]+)(#?)", 
                    "<a class=\"link\" href=\"/message?category=message&key=\\g<1>\">#\\g<1>\\g<2></a>", item)
            else:
                token = tokens[index]
                token = token.replace("&", "&amp;")
                token = token.replace("<", "&lt;")
                token = token.replace(">", "&gt;")
                tokens[index] = token

        line = '&nbsp;'.join(tokens)
        line = line.replace("\t", '&nbsp;&nbsp;&nbsp;&nbsp;')
        lines.append(line)
    return "<br/>".join(lines)

def split_words(search_key):
    """拆分字符
        >>> split_words("abc is good")
        ["abc", "is", "good"]
        >>> split_words("中文测试")
        ["中", "文", "测", "试"]
        >>> split_words("中文123")
        ["中", "文", "123"]
        >>> split_words("中文123测试")
        ["中", "文", "123", "测", "试"]
    """
    search_key_lower = search_key.lower()
    words = []
    p_start = 0
    for p in range(len(search_key_lower) + 1):
        if p == len(search_key_lower):
            if p > p_start:
                word = search_key_lower[p_start:p]
                words.append(word)
            break

        c = search_key_lower[p]
        if isblank(c):
            # 空格断字
            if p > p_start:
                word = search_key_lower[p_start:p]
                words.append(word)
            p_start = p + 1
        elif is_cjk(c):
            # 中日韩字符集采用单字模式
            if p > p_start:
                words.append(search_key_lower[p_start:p])
            words.append(c)
            p_start = p + 1
        else:
            # 其他字符
            continue
    # print(words)
    return words

 
if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
