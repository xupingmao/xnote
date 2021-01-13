# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/01/10 14:36:09
# @modified 2021/01/14 00:26:58

"""标记文本解析"""
import os
from urllib.parse import quote, unquote

IMG_EXT_SET = set([".png", ".jpg", ".gif"])

def invoke_deco(prefix = ""):
    """日志装饰器"""
    def deco(func):
        def handle(*args, **kw):
            try:
                result = func(*args, **kw)
                print(prefix, args, kw, result)
                return result
            except Exception as e:
                print("exception occurs", prefix, args, kw)
                raise e
        return handle
    return deco

def is_img_file(filename):
    """根据文件后缀判断是否是图片"""
    name, ext = os.path.splitext(filename)
    return ext.lower() in IMG_EXT_SET

def set_img_file_ext(img_set):
    global IMG_EXT_SET
    IMG_EXT_SET = img_set

def escape_html(text):
    # 必须先处理&
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace(" ", "&nbsp;")
    text = text.replace("'", "&#39;")
    text = text.replace("\n", "<br/>")
    return text

class TextParserBase(object):

    """文本解析工具， 参考 tornado template"""
    def init(self, text):
        text = text.replace("\r", "")
        text = text.replace(u'\xad', '\n')

        self.text = text
        self.str_token = ""
        self.tokens = []
        # 当前读取的字符下标
        self.i = 0
        self.length = len(text)
        self.max_index = self.length - 1

    def current(self):
        """当前的字符，如果越界了，返回None"""
        if self.i < self.length:
            return self.text[self.i]
        return None

    def next(self):
        """往后读取一个字符，返回读取的字符，如果已经读完了，返回None"""
        if self.i < self.max_index:
            self.i += 1
            return self.text[self.i]
        return None

    def hasnext(self):
        return self.i < self.length

    def startswith(self, target):
        length = len(target)
        return self.text[self.i:self.i+length] == target

    def find(self, target):
        return self.text.find(target, self.i)

    def find_blank(self):
        """找到一个空白字符"""
        i = self.i
        for i in range(self.i, self.length):
            c = self.text[i]
            if c in " \t\n\r":
                return i

        return -1

    def stash_char(self, c):
        """暂存一个字符"""
        self.str_token += c

    def save_str_token(self):
        if self.str_token != "":
            token = self.str_token
            token = escape_html(token)
            self.tokens.append(token)
        self.str_token = ""

    def read_till_blank(self):
        """从当前字符开始，找到空白字符为止"""
        end = self.find_blank()
        if end < 0:
            found = self.text[self.i:]
            self.i = self.max_index
        else:
            found = self.text[self.i:end]
            # 当前处于第一个空白字符
            self.i = end - 1
        return found

    def read_number(self):
        for i in range(self.i, self.length):
            c = self.text[i]
            if not c.isdigit():
                token = self.text[self.i:i]
                # 当前处于最后一个数字下标
                self.i = i - 1
                return token
        token = self.text[self.i:]
        self.i = i
        return token

    def parse(self, text):
        raise Exception("parse() must be implemented by child class")


class TextParser(TextParserBase):

    mark_book_single_flag = False

    mark_number_flag = False

    def read_till_target(self, end_char):
        end = self.text.find(end_char, self.i+1)
        if end < 0:
            key = self.text[self.i:]
            self.i = self.max_index
        else:
            key = self.text[self.i:end+1]
            # 包含end_char
            self.i = end
        return key

    def mark_topic(self):
        """话题转为搜索关键字的时候去掉前后的#符号"""
        self.save_str_token()
        key0 = self.read_till_target("#")
        key = key0.lstrip("#")
        key = key.rstrip("#")
        quoted_key = quote(key)
        value = escape_html(key0)
        token = "<a class=\"link\" href=\"/message?category=message&key=%s\">%s</a>" % (quoted_key, value)
        self.tokens.append(token)

    def mark_http(self):
        self.save_str_token()
        link  = self.read_till_blank()
        token = '<a target="_blank" href="%s">%s</a>' % (link, link)
        self.tokens.append(token)

    def mark_https(self):
        return self.mark_http()

    def mark_book(self):
        return self.mark_tag_single("》")

    def mark_book_single(self):
        return self.mark_tag_single(">")

    def mark_number(self):
        self.save_str_token()
        number = self.read_number()
        token = "<a class=\"link\" href=\"/message?category=message&key=%s\">%s</a>" % (number, number)
        self.tokens.append(token)
        return token

    def mark_tag_single(self, end_char):
        self.save_str_token()
        key = self.read_till_target(end_char)
        quoted_key = quote(key)
        value = escape_html(key)
        token = "<a class=\"link\" href=\"/message?category=message&key=%s\">%s</a>" % (quoted_key, value)
        self.tokens.append(token)

    def mark_file(self):
        self.save_str_token()
        href = self.read_till_blank()
        href = href[7:]
        if is_img_file(href):
            token = '<img class="chat-msg-img x-photo" alt="%s" src="%s">' % (href, href)
            self.tokens.append(token)
        else:
            name = href[href.rfind("/")+1:]
            # 尝试urldecode名称
            name = unquote(name)
            token = '<a href="%s">%s</a>' % (href, name)
            self.tokens.append(token)

    def parse(self, text):
        self.init(text)

        c = self.current()
        while c != None:
            if c == '#':
                self.mark_topic()
            elif c == '《':
                self.mark_book()
            elif self.mark_book_single_flag and c == '<':
                self.mark_book_single()
            elif c == '\n':
                self.stash_char(c)
                self.save_str_token()
            elif self.mark_number_flag and c.isdigit():
                self.mark_number()
            elif self.startswith("http://"):
                self.mark_http()
            elif self.startswith("https://"):
                self.mark_https()
            elif self.startswith("file://"):
                self.mark_file()
            else:
                self.stash_char(c)
            c = self.next()

        self.save_str_token()
        return self.tokens

def runtest():
    text   = """#Topic1# #Topic2 Test#
    #中文话题#
    This is a new line
    图片file:///data/temp/1.png
    文件file:///data/temp/1.zip
    link1:http://abc.com/test?name=1
    link2:https://abc.com/test?name=1&age=2 text after link
    数字123456END
    <code>test</code>
    """

    parser = TextParser()
    tokens = parser.parse(text)
    # print(tokens)
    print("input: %s" % text)
    print("output:")
    result = "".join(tokens)
    result = result.replace("<br/>", "\n<br/>\n")
    print(result)

if __name__ == '__main__':
    runtest()

