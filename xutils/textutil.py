# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2017/?/?
# @modified 2022/04/16 18:18:24

"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-04-17 17:04:15
@LastEditors  : xupingmao
@LastEditTime : 2024-05-03 12:41:40
@FilePath     : /xnote/xutils/textutil.py
@Description  : 文本处理工具
"""

import re
import random
import json
import inspect
import hashlib
import base64
from xutils.imports import is_str, ConfigParser
from xutils.textutil_url import *
from collections import OrderedDict

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
        raise TypeError("unsupported type:%s" % type(words))

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

def count_end_nl(content):
    count = 0
    i = len(content) - 1
    for i in range(i, -1, -1):
        c = content[i]
        if c == '\n':
            count += 1
        elif c == '\r':
            continue
        else:
            break
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

def is_number(value):
    try:
        float(value)
        return True
    except:
        return False

def is_json(value):
    try:
        json.loads(value)
        return True
    except:
        return False

"""解析文本的方法
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

def remove_head(text, head):
    """移除头部的字符
        >>> remove_head("person.age", "person.")
        "age"
        >>> remove_head("person.age", "test")
        "person.age"
    """
    if text is None or head is None:
        return text

    if not text.startswith(head):
        return text

    return text[len(head):]

def remove_tail(text, tail):
    """移除尾部的字符
        >>> remove_tail("person.age", ".age")
        "person"
        >>> remove_tail("person.age", "name")
        "person.age"
    """
    assert is_str(tail)
    
    if text is None:
        return text

    if not text.endswith(tail):
        return text

    return text[:-len(tail)]

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
    """这个其实就是通配符，参考 fnmatch 模块
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
    assert isinstance(cache, list)
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

def random_number_str(length):
    return random_string(length, "0123456789")

def parse_config_text(text, ret_type = 'list'):
    return parse_prop_text(text, ret_type)

def parse_config_text_to_dict(text) -> dict:
    result = parse_prop_text(text, "dict")
    assert isinstance(result, dict)
    return result

def parse_prop_text(text, ret_type = "dict"):
    from xutils.text_parser_properties import parse_prop_text as parse_prop_text_impl
    return parse_prop_text_impl(text, ret_type)

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
    """生成UUID"""
    import uuid
    return uuid.uuid4().hex

def create_uuid():
    """生成UUID"""
    return generate_uuid()

def _encode_json(obj):
    """基本类型不会拦截"""
    if inspect.isfunction(obj):
        return "<function>"
    elif inspect.isclass(obj):
        return "<class>"
    elif inspect.ismodule(obj):
        return "<module>"
    return str(obj)

def tojson(obj, format=False, ensure_ascii=False):
    if format:
        return json.dumps(obj, sort_keys=True, default=_encode_json, indent=2, ensure_ascii=ensure_ascii)
    else:
        return json.dumps(obj, default=_encode_json, ensure_ascii=ensure_ascii)

def tojson_ignore_error(obj, format=False):
    try:
        return tojson(obj, format)
    except Exception as e:
        return None

def parse_json(json_str, ignore_error = False):
    try:
        return json.loads(json_str)
    except Exception as e:
        if ignore_error:
            return None
        else:
            raise e

def set_doctype(type):
    print("#!%s\n" % type)

def get_doctype(text):
    if text.startswith("#!html"):
        return "html"
    return "text"


def is_img_file(filename):
    """根据文件后缀判断是否是图片"""
    import os
    from xnote.core import xconfig
    name, ext = os.path.splitext(filename)
    return ext.lower() in xconfig.FS_IMG_EXT_LIST

def mark_text(content):
    from xnote.core import xconfig
    from xutils.text_parser import TextParser, set_img_file_ext
    # 设置图片文集后缀
    set_img_file_ext(xconfig.FS_IMG_EXT_LIST)

    parser = TextParser()
    tokens = parser.parse(content)
    return "".join(tokens)


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


def try_split_key_value(line, token=":"):
    if line is None:
        return None, None
    line = line.strip()
    if line.startswith("#"):
        return None, None
    cols = line.split(token, 1)
    if len(cols) != 2:
        return None, None
    return cols[0].strip(), cols[1].strip()

def split_key_value(line):
    for token in (":", "=", " "):
        key, value = try_split_key_value(line, token)
        if key != None:
            return key, value
    return None, None


#################################################################
##   Html Utilities, Python 2 do not have this file
#################################################################

def html_escape(s, quote=True):
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true (the default), the quotation mark
    characters, both double quote (") and single quote (') characters are also
    translated.
    """
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace('\'', "&#x27;")
    return s

def escape_html(text):
    """html转义, 参考`lib/tornado/escape.py`"""
    # 必须先处理&
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace(" ", "&nbsp;")
    text = text.replace("'", "&#39;")
    text = text.replace("\n", "<br/>")
    return text

def urlsafe_b64encode(text):
    """URL安全的base64编码，注意Python自带的方法没有处理填充字符=
    @param {str} text 待编码的字符
    """
    b64result = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
    return b64result.rstrip("=")


def urlsafe_b64decode(text):
    """URL安全的base64解码，注意Python自带的方法没有处理填充字符=
    @param {str} text 编码后的字符
    """
    padding = 4- len(text) % 4
    text = text + '=' * padding
    return base64.urlsafe_b64decode(text).decode("utf-8")

b64encode = urlsafe_b64encode
b64decode = urlsafe_b64decode


def b32encode(text):
    result = base64.b32encode(text.encode('utf-8'))
    return result.decode('utf-8').rstrip("=")

def b32decode(enc_text):
    padding = 8 - len(enc_text) % 8
    enc_text = enc_text + "=" * padding
    return base64.b32decode(enc_text).decode("utf-8")

def encode_uri_component(text):
    # quoted = quote_unicode(text)
    # quoted = quoted.replace("?", "%3F")
    # quoted = quoted.replace("&", "%26")
    # quoted = quoted.replace(" ", "%20")
    # quoted = quoted.replace("=", "%3D")
    # quoted = quoted.replace("+", "%2B")
    # quoted = quoted.replace("#", "%23")
    return quote(text)

def md5_hex(string=""):
    """生成MD5哈希校验码, 长度是32"""
    return hashlib.md5(string.encode("utf-8")).hexdigest()

def sha1_hex(string=""):
    """生产SHA-1哈希校验码, 长度是40"""
    return hashlib.sha1(string.encode("utf-8")).hexdigest()
        
class Properties(object): 
    
    """Properties 文件处理器"""
    def __init__(self, fileName, ordered = True): 
        self.ordered = ordered
        self.fileName = fileName
        self.properties = None     # 层次化的属性
        self.flat_properties = {}  # 摊平的属性键值对
        self.load_properties()

    def new_dict(self):
        if self.ordered:
            return OrderedDict()
        else:
            return {}

    def _set_dict(self, strName, dict, value): 
        strName = strName.strip()
        value = value.strip()

        if strName == "":
            return

        if(strName.find('.')>0): 
            k = strName.split('.')[0] 
            dict.setdefault(k, self.new_dict()) 
            self._set_dict(strName[len(k)+1:], dict[k], value)
            return
        else: 
            dict[strName] = value 
            return 

    def load_properties(self): 
        self.properties = self.new_dict()
        self.flat_properties = self.new_dict()
        with open(self.fileName, 'r', encoding="utf-8") as pro_file: 
            for line in pro_file.readlines(): 
                line = line.strip().replace('\n', '') 
                if line.find("#")!=-1: 
                    line=line[0:line.find('#')] 
                if line.find('=') > 0: 
                    strs = line.split('=') 
                    strs[1]= line[len(strs[0])+1:] 
                    self._set_dict(strs[0], self.properties,strs[1]) 
                    self.flat_properties[strs[0].strip()] = strs[1].strip()
        return self.properties

    def get_properties(self):
        return self.properties

    def get_property(self, key, default_value=None):
        return self.flat_properties.get(key, default_value)

    def reload(self):
        self.load_properties()

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
