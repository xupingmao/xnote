# encoding=utf-8

import unittest
from xutils.text_parser import TextParser, TextToken, TopicToken
from xutils.text_parser import TokenType
from xutils.text_parser import StrongToken
from xutils.text_parser import ImageToken

class TestTextParser(unittest.TestCase):

    def print_head(self, message):
        width  = 60
        length = len(message)
        left  = (width - length) // 2
        right = width - length - left
        print()
        print("-" * left, message, "-" * right)

    def test_topic1(self, ):
        self.print_head("Topic Test 1")
        text = "#Topic1# Text"
        parser = TextParser()
        tokens = parser.parse(text)
        print("text=%r" % text)
        print(tokens)

        struct_tokens = parser.parse_to_tokens(text)
        print("struct_tokens", struct_tokens)
        assert len(struct_tokens) == 2
        assert struct_tokens[0] == TopicToken("#Topic1#")
        assert struct_tokens[1] == TextToken(" Text")

    def test_topic2(self):
        self.print_head("Topic Test 2")
        text = "#Topic2 Bank# Text"
        parser = TextParser()
        tokens = parser.parse(text)
        print("text=%r" % text)
        print(tokens)

    def test_topic3(self):
        self.print_head("Topic Test 3")
        text = "#NewLineTopic \nBank# Text"
        parser = TextParser()
        tokens = parser.parse(text)
        print("text=%r" % text)
        print(tokens)
        print("keywords=%s" % parser.keywords)


    def test_strong_normal(self):
        self.print_head("runtest_strong_normal")
        text = "test**mark**end"
        parser = TextParser()
        tokens = parser.parse(text)
        print(tokens)
        assert tokens[0] == "test"
        assert tokens[1] == "<span class=\"msg-strong\">mark</span>"
        assert tokens[2] == "end"

        struct_tokens = parser.parse_to_tokens(text)
        assert struct_tokens[0] == TextToken("test")
        assert struct_tokens[1] == StrongToken("**mark**")
        assert struct_tokens[2] == TextToken("end")

    def test_strong_nl(self):
        self.print_head("runtest_strong_nl")
        text = "test**mark\n**end"
        parser = TextParser()
        tokens = parser.parse(text)
        assert tokens[0] == "test"
        assert tokens[1] == "**mark<br/>"
        assert tokens[2] == "**"
        assert tokens[3] == "end"

    def test_strong_no_match(self):
        self.print_head("runtest_strong_no_match")
        text = "test***"
        parser = TextParser()
        tokens = parser.parse(text)
        print(tokens)
        assert tokens[0] == "test"
        assert tokens[1] == "**"
        assert tokens[2] == "*"

    def test_image(self):
        text = "图片file:///data/temp/1.png"
        parser = TextParser()
        tokens = parser.parse(text)
        print(tokens)
        assert tokens[0] == "图片"
        assert tokens[1] == '<div class="msg-img-box"><img class="msg-img x-photo" alt="/data/temp/1.png" src="/data/temp/1.png"></div>'
    
    def test_other(self):
        text = """#Topic1# #Topic2 Test#
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

        struct_tokens = parser.parse_to_tokens(text)
        # print("struct_tokens:", struct_tokens)
        for token in struct_tokens:
            print(token)

        assert struct_tokens[0] == TopicToken("#Topic1#")
        assert struct_tokens[1] == TextToken(" ")
        assert struct_tokens[2] == TopicToken("#Topic2 Test#")
        assert struct_tokens[3] == TextToken("\n")
        assert struct_tokens[4] == TopicToken("#中文话题#")
        assert struct_tokens[5] == TextToken("\n")
        assert struct_tokens[6] == TextToken("This is a new line\n")
        assert struct_tokens[7] == TextToken("图片")

    def test_multi_img(self):
        text = "file:///data/temp/1.png\nfile:///data/temp/2.png"
        parser = TextParser()
        tokens = parser.parse_to_tokens(text)
        assert len(tokens) == 2
        assert tokens[0] == ImageToken("file:///data/temp/1.png", "/data/temp/1.png")
        assert tokens[1] == ImageToken("\nfile:///data/temp/2.png", "/data/temp/2.png")
