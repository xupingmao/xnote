# -*- coding: utf-8 -*-
"""Coverage tests for xutils/fsutil.py and xutils/textutil.py.

These are pure file/text utilities and are safe to test directly without a
live server. File operations use temporary directories so the tests are
hermetic and clean up after themselves.
"""
import os
import sys
import json
import shutil
import tempfile
import unittest

import xutils
import xutils.fsutil as fsutil
import xutils.textutil as textutil
from xutils.base import Storage


# ---------------------------------------------------------------------------
# textutil tests
# ---------------------------------------------------------------------------

class TestTextContains(unittest.TestCase):

    def test_contains_all_str(self):
        self.assertTrue(textutil.contains_all("abc is good", "abc"))
        self.assertTrue(textutil.contains_all("you are right", "rig"))
        self.assertFalse(textutil.contains_all("you are right", "xyz"))

    def test_contains_all_seq(self):
        self.assertTrue(textutil.contains_all("hello,world,yep", ["hello", "yep"]))
        self.assertFalse(textutil.contains_all("hello,world,yep", ["hello", "nope"]))

    def test_contains_all_unsupported(self):
        with self.assertRaises(TypeError):
            textutil.contains_all("abc", 123)

    def test_text_contains_alias(self):
        self.assertTrue(textutil.text_contains("abc", "a"))

    def test_contains_any_str(self):
        self.assertTrue(textutil.contains_any("abc", "b"))
        self.assertFalse(textutil.contains_any("abc", "z"))

    def test_contains_any_seq(self):
        self.assertTrue(textutil.contains_any("abc", ["x", "b"]))
        self.assertFalse(textutil.contains_any("abc", ["x", "y"]))

    def test_contains_any_unsupported(self):
        with self.assertRaises(TypeError):
            textutil.contains_any("abc", 123)


class TestTextCharChecks(unittest.TestCase):

    def test_count_alpha(self):
        self.assertEqual(textutil.count_alpha("ab12cd"), 4)
        self.assertEqual(textutil.count_alpha("123"), 0)

    def test_count_digit(self):
        self.assertEqual(textutil.count_digit("ab12cd"), 2)
        self.assertEqual(textutil.count_digit("abc"), 0)

    def test_count_end_nl(self):
        self.assertEqual(textutil.count_end_nl("a\n\n"), 2)
        self.assertEqual(textutil.count_end_nl("a\r\n"), 1)  # \r is skipped, \n counted
        self.assertEqual(textutil.count_end_nl("a\nb"), 0)
        self.assertEqual(textutil.count_end_nl(""), 0)

    def test_isalpha_helpers(self):
        self.assertTrue(textutil._isalpha("a"))
        self.assertFalse(textutil._isalpha("1"))
        self.assertTrue(textutil._isdigit("1"))
        self.assertFalse(textutil._isdigit("a"))
        self.assertTrue(textutil._isalnum("1"))
        self.assertTrue(textutil._isalnum("a"))
        self.assertFalse(textutil._isalnum("."))

    def test_chk_list(self):
        self.assertTrue(textutil._chk_list("abc", textutil._isalpha))
        self.assertFalse(textutil._chk_list("ab1", textutil._isalpha))

    def test_isalpha_isalnum_isdigit(self):
        self.assertTrue(textutil.isalpha("abc"))
        self.assertFalse(textutil.isalpha("12abc"))
        self.assertTrue(textutil.isalnum("123abc"))
        self.assertFalse(textutil.isalnum("-abc-"))
        self.assertTrue(textutil.isdigit("123"))
        self.assertFalse(textutil.isdigit("abc111"))

    def test_isblank(self):
        self.assertTrue(textutil.isblank("  \n\t\r"))
        self.assertFalse(textutil.isblank(" a "))
        self.assertTrue(textutil.isblank(""))

    def test_is_cjk(self):
        self.assertTrue(textutil.is_cjk(u"中"))
        self.assertTrue(textutil.is_cjk(u"𠀀"))  # ext B range
        self.assertFalse(textutil.is_cjk("a"))
        self.assertFalse(textutil.is_cjk("1"))

    def test_is_number(self):
        self.assertTrue(textutil.is_number("123"))
        self.assertTrue(textutil.is_number("12.5"))
        self.assertTrue(textutil.is_number(3))
        self.assertFalse(textutil.is_number("abc"))

    def test_is_json(self):
        self.assertTrue(textutil.is_json('{"a":1}'))
        self.assertTrue(textutil.is_json('[1,2]'))
        self.assertFalse(textutil.is_json('not json'))


class TestTextManipulate(unittest.TestCase):

    def test_remove(self):
        self.assertEqual(textutil.remove("this is a bat", "bat"), "this is a ")

    def test_remove_prefix(self):
        self.assertEqual(textutil.remove_prefix("person.age", "person."), "age")
        self.assertEqual(textutil.remove_prefix("person.age", "test"), "person.age")
        self.assertEqual(textutil.remove_prefix(None, "x"), None)
        self.assertEqual(textutil.remove_prefix("person.age", None), "person.age")
        self.assertEqual(textutil.remove_head("person.age", "person."), "age")

    def test_remove_suffix(self):
        self.assertEqual(textutil.remove_suffix("person.age", ".age"), "person")
        self.assertEqual(textutil.remove_suffix("person.age", "name"), "person.age")
        self.assertEqual(textutil.remove_tail("person.age", ".age"), "person")

    def test_add_prefix(self):
        self.assertEqual(textutil.add_prefix("hello", "world"), "worldhello")
        self.assertEqual(textutil.add_prefix("worldhello", "world"), "worldhello")

    def test_add_suffix(self):
        self.assertEqual(textutil.add_suffix("hello", "world"), "helloworld")
        self.assertEqual(textutil.add_suffix("helloworld", "world"), "helloworld")

    def test_between(self):
        self.assertEqual(textutil.between("start words end", "start", "end"), " words ")
        self.assertEqual(textutil.between("abc", "x", "y"), "")
        self.assertEqual(textutil.between("start only", "start", "end"), "")

    def test_replace_between(self):
        result = textutil.replace_between("a [x] b", "[", "]", "NEW")
        self.assertEqual(result, "a [NEW] b")
        self.assertIsNone(textutil.replace_between("abc", "[", "]", "NEW"))
        self.assertIsNone(textutil.replace_between("a [x b", "[", "]", "NEW"))

    def test_split_chars(self):
        result = textutil.split_chars("a b\n\tc")
        self.assertEqual(result, ["a", "b", "c"])
        # non-printable filtered
        self.assertEqual(textutil.split_chars("\x00z"), ["z"])

    def test_split_first(self):
        self.assertEqual(textutil.split_first("find a.name b.name"), ("find", "a.name b.name"))
        self.assertEqual(textutil.split_first("find"), ("find", ""))
        self.assertEqual(textutil.split_first("find-a.name", "-"), ("find", "a.name"))

    def test_find(self):
        self.assertEqual(textutil.find("hello,world", "hello"), ["hello,world"])
        self.assertEqual(textutil.find("yes", ""), [])
        self.assertEqual(textutil.find("hell1,world\nhello,kid", "hello", True),
                         ["0002:hello,kid"])
        # case sensitive
        self.assertEqual(textutil.find("Hello", "hello", ignore_case=False), [])
        # list of keys
        self.assertEqual(textutil.find("hello world", ["hello", "world"]),
                         ["hello world"])

    def test_replace(self):
        self.assertEqual(textutil.replace("abc is good", "iS", "is not", True),
                         "abc is not good")
        self.assertEqual(textutil.replace("this is a long story", "loNg", "-long-", True),
                         "this is a -long- story")
        self.assertEqual(textutil.replace("use Template", "template", "<k>?</k>", True, True),
                         "use <k>Template</k>")
        # no ignore case
        self.assertEqual(textutil.replace("abc", "b", "x"), "axc")
        # no template, multiple matches
        self.assertEqual(textutil.replace("abab", "ab", "x"), "xx")

    def test_like(self):
        self.assertTrue(textutil.like("hello,world", "hello*"))
        self.assertTrue(textutil.like("yes", "y?s"))
        self.assertFalse(textutil.like("what", "n*"))

    def test_byte2str(self):
        self.assertEqual(textutil.byte2str("中文".encode("utf-8")), "中文")
        self.assertEqual(textutil.byte2str("abc".encode("ascii")), "abc")

    def test_edit_distance(self):
        self.assertEqual(textutil.edit_distance("ab", "a"), 1)
        self.assertEqual(textutil.edit_distance("abc", "ac"), 1)
        self.assertEqual(textutil.edit_distance("abc", "abc"), 0)
        self.assertEqual(textutil.edit_distance("", "abc"), 3)
        self.assertEqual(textutil.edit_distance("abc", ""), 3)
        # custom replace step
        self.assertEqual(textutil.edit_distance("ab", "cd", replace_step=1), 2)

    def test_jaccard(self):
        self.assertAlmostEqual(textutil.jaccard_similarity("abc", "abc"), 1.0)
        self.assertAlmostEqual(textutil.jaccard_similarity("abc", "xyz"), 0.0)
        self.assertAlmostEqual(textutil.jaccard_distance("abc", "abc"), 0.0)
        self.assertAlmostEqual(textutil.jaccard_distance("abc", "xyz"), 1.0)


class TestTextRandom(unittest.TestCase):

    def test_random_string(self):
        s = textutil.random_string(10)
        self.assertEqual(len(s), 10)
        s2 = textutil.random_string(5, "ab")
        self.assertTrue(all(c in "ab" for c in s2))

    def test_random_number_str(self):
        s = textutil.random_number_str(8)
        self.assertEqual(len(s), 8)
        self.assertTrue(s.isdigit())


class TestTextParse(unittest.TestCase):

    def test_parse_config_text(self):
        text = "name=x\nage=1\n"
        d = textutil.parse_config_text(text, "dict")
        self.assertEqual(d["name"], "x")
        lst = textutil.parse_config_text(text, "list")
        self.assertIsInstance(lst, list)

    def test_parse_config_text_to_dict(self):
        d = textutil.parse_config_text_to_dict("a=1\nb=2\n")
        self.assertEqual(d["a"], "1")
        self.assertEqual(d["b"], "2")

    def test_parse_prop_text(self):
        d = textutil.parse_prop_text("a=1\nb=2\n", "dict")
        self.assertEqual(d["a"], "1")

    def test_parse_ini_text(self):
        text = "[section1]\nkey1=value1\nkey2=value2\n"
        data = textutil.parse_ini_text(text)
        self.assertEqual(data["section1"]["key1"], "value1")
        self.assertEqual(data["section1"]["key2"], "value2")

    def test_parse_simple_command(self):
        self.assertEqual(textutil.parse_simple_command("find a.name b.name"),
                         ("find", "a.name b.name"))
        self.assertEqual(textutil.parse_simple_command("find"), ("find", ""))
        self.assertEqual(textutil.parse_simple_command("find    a.name"),
                         ("find", "a.name"))
        self.assertEqual(textutil.parse_simple_command("find-name \t lalala"),
                         ("find-name", "lalala"))


class TestTextShortCamel(unittest.TestCase):

    def test_get_short_text(self):
        self.assertEqual(textutil.get_short_text("abc", 5), "abc")
        self.assertEqual(textutil.get_short_text("abcdefg", 5), "ab...")
        self.assertEqual(textutil.get_short_text("abcd", 5), "abcd")
        self.assertEqual(textutil.get_short_text("中文12345678", 5), "中文...")
        with self.assertRaises(Exception):
            textutil.get_short_text("abc", 2)
        # aliases
        self.assertEqual(textutil.short_text("abcdefg", 5), "ab...")
        self.assertEqual(textutil.shortfor("abcdefg", 5), "ab...")
        self.assertEqual(textutil.get_ellipsis_text("abcdefg", 5), "ab...")

    def test_get_camel_case(self):
        self.assertEqual(textutil.get_camel_case("name"), "name")
        self.assertEqual(textutil.get_camel_case("get_name"), "getName")
        self.assertEqual(textutil.get_camel_case("get_my_name", True), "GetMyName")
        self.assertEqual(textutil.to_camel_case("a_b"), "aB")

    def test_get_underscore(self):
        self.assertEqual(textutil.get_underscore("getName"), "get_name")
        self.assertEqual(textutil.get_underscore("GetName"), "get_name")
        self.assertEqual(textutil.to_underscore("GetName"), "get_name")


class TestTextUuidJson(unittest.TestCase):

    def test_uuid(self):
        u = textutil.generate_uuid()
        self.assertEqual(len(u), 32)
        self.assertEqual(len(textutil.create_uuid()), 32)

    def test_tojson(self):
        self.assertEqual(textutil.tojson({"a": 1}), '{"a":1}')
        self.assertIn("\n", textutil.tojson({"a": 1}, format=True))

    def test_tojson_ignore_error(self):
        # happy path: returns the json string (jsonutil is lenient)
        self.assertEqual(textutil.tojson_ignore_error({"a": 1}), '{"a":1}')
        self.assertIsInstance(textutil.tojson_ignore_error(object()), str)

    def test_parse_json(self):
        self.assertEqual(textutil.parse_json('{"a":1}'), {"a": 1})
        self.assertIsNone(textutil.parse_json("bad", ignore_error=True))
        with self.assertRaises(Exception):
            textutil.parse_json("bad")

    def test_set_doctype(self):
        # just ensure it does not raise
        textutil.set_doctype("text")

    def test_get_doctype(self):
        self.assertEqual(textutil.get_doctype("#!html"), "html")
        self.assertEqual(textutil.get_doctype("normal text"), "text")


class TestTextWords(unittest.TestCase):

    def test_split_words(self):
        self.assertEqual(textutil.split_words("abc is good"), ["abc", "is", "good"])
        self.assertEqual(textutil.split_words("中文测试"), ["中", "文", "测", "试"])
        self.assertEqual(textutil.split_words("中文123"), ["中", "文", "123"])
        self.assertEqual(textutil.split_words("中文123测试"),
                         ["中", "文", "123", "测", "试"])

    def test_try_split_key_value(self):
        self.assertEqual(textutil.try_split_key_value(None), (None, None))
        self.assertEqual(textutil.try_split_key_value("# comment"), (None, None))
        self.assertEqual(textutil.try_split_key_value("a: b"), ("a", "b"))
        self.assertEqual(textutil.try_split_key_value("a = b", token="="), ("a", "b"))
        self.assertEqual(textutil.try_split_key_value("no separator"), (None, None))

    def test_split_key_value(self):
        self.assertEqual(textutil.split_key_value("a: b"), ("a", "b"))
        self.assertEqual(textutil.split_key_value("a = b"), ("a", "b"))
        self.assertEqual(textutil.split_key_value("a b"), ("a", "b"))
        self.assertEqual(textutil.split_key_value("# comment"), (None, None))


class TestTextHtml(unittest.TestCase):

    def test_html_escape(self):
        self.assertEqual(textutil.html_escape("&<>"), "&amp;&lt;&gt;")
        self.assertEqual(textutil.html_escape('a"b\'c', quote=True),
                         "a&quot;b&#x27;c")
        self.assertEqual(textutil.html_escape('a"b', quote=False), 'a"b')

    def test_escape_html(self):
        self.assertEqual(textutil.escape_html("&<>"), "&amp;&lt;&gt;")
        self.assertEqual(textutil.escape_html("a b\nc", escape_blank=True),
                         "a&nbsp;b<br/>c")
        self.assertEqual(textutil.escape_html("a b", escape_blank=False), "a b")


class TestTextBase64(unittest.TestCase):

    def test_encode_decode_base64(self):
        s = "hello 中文"
        enc = textutil.encode_base64(s)
        self.assertEqual(textutil.decode_base64(enc), s)
        # bytes input
        enc2 = textutil.encode_base64(b"abc")
        self.assertEqual(textutil.decode_base64(enc2), "abc")
        # string with no padding after strip
        enc_no_pad = textutil.encode_base64("abc123")
        self.assertNotIn("=", enc_no_pad)
        self.assertEqual(textutil.decode_base64(enc_no_pad), "abc123")
        # no strip keeps padding
        enc3 = textutil.encode_base64("ab", strip=False)
        self.assertIn("=", enc3)
        self.assertEqual(textutil.decode_base64(enc3), "ab")
        # aliases
        self.assertEqual(textutil.b64encode(s), enc)
        self.assertEqual(textutil.b64decode(enc), s)
        self.assertEqual(textutil.urlsafe_b64encode(s), enc)
        self.assertEqual(textutil.urlsafe_b64decode(enc), s)

    def test_decode_base64_empty(self):
        self.assertEqual(textutil.decode_base64(""), "")

    def test_encode_decode_base32(self):
        s = "hello"
        enc = textutil.encode_base32(s)
        self.assertEqual(textutil.decode_base32(enc), s)
        enc2 = textutil.encode_base32(b"abc")
        self.assertEqual(textutil.decode_base32(enc2), "abc")
        enc3 = textutil.encode_base32("abc", strip=False)
        self.assertEqual(textutil.decode_base32(enc3), "abc")
        self.assertEqual(textutil.b32encode(s), enc)
        self.assertEqual(textutil.b32decode(enc), s)

    def test_encode_uri_component(self):
        self.assertEqual(textutil.encode_uri_component("a b"), "a%20b")

    def test_to_bytes(self):
        self.assertEqual(textutil.to_bytes("a"), b"a")
        self.assertEqual(textutil.to_bytes(b"a"), b"a")


class TestTextHashes(unittest.TestCase):

    def test_md5_sha(self):
        self.assertEqual(textutil.md5_hex("abc"),
                         "900150983cd24fb0d6963f7d28e17f72")
        self.assertEqual(textutil.sha1_hex("abc"),
                         "a9993e364706816aba3e25717850c26c9cd0d89d")
        self.assertEqual(
            textutil.sha256_hex("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertEqual(
            textutil.sha512_hex("abc"),
            "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
            "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f")


class TestTextSafeStr(unittest.TestCase):

    def test_safe_str(self):
        self.assertEqual(textutil.safe_str(None), "")
        self.assertEqual(textutil.safe_str(b"abc"), "abc")
        self.assertEqual(textutil.safe_str(123), "123")
        self.assertEqual(textutil.safe_str("hello", max_length=3), "hel")
        self.assertEqual(textutil.safe_str("hello", max_length=-1), "hello")

    def test_append_text(self):
        self.assertEqual(textutil.append_text("", "a"), "a")
        self.assertEqual(textutil.append_text("a", ""), "a")
        self.assertEqual(textutil.append_text("a", "b"), "a, b")
        self.assertEqual(textutil.append_text("a", "b", sep=";"), "a;b")


class TestTextProperties(unittest.TestCase):

    def test_properties(self):
        content = "name=xupingmao\nage=18\nuser.name=test\n# comment\nempty=\n"
        with tempfile.NamedTemporaryFile("w", suffix=".properties",
                                          delete=False, encoding="utf-8") as fp:
            fp.write(content)
            path = fp.name
        try:
            props = textutil.Properties(path, ordered=True)
            self.assertEqual(props.get_property("name"), "xupingmao")
            self.assertEqual(props.get_property("age"), "18")
            self.assertEqual(props.get_property("user.name"), "test")
            self.assertEqual(props.get_property("empty"), "")
            self.assertEqual(props.get_property("missing", "default"), "default")
            # hierarchical
            self.assertEqual(props.get_properties()["user"]["name"], "test")
            props.reload()
            self.assertEqual(props.get_property("name"), "xupingmao")
        finally:
            os.remove(path)


class TestTextFileType(unittest.TestCase):

    def test_is_img_file_xconfig(self):
        # depends on xnote.core.xconfig (works standalone)
        self.assertTrue(textutil.is_img_file("a.png"))
        self.assertFalse(textutil.is_img_file("a.txt"))

    def test_mark_text(self):
        result = textutil.mark_text("hello world")
        self.assertIsInstance(result, str)
        self.assertIn("hello", result)


# ---------------------------------------------------------------------------
# fsutil tests
# ---------------------------------------------------------------------------

class TestFsutilPath(unittest.TestCase):

    def test_get_real_path(self):
        self.assertEqual(fsutil.get_real_path(""), "")
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "real.txt")
            with open(fpath, "w") as fp:
                fp.write("x")
            self.assertEqual(fsutil.get_real_path(fpath), fpath)
            # nonexistent returns path
            self.assertEqual(fsutil.get_real_path(os.path.join(d, "nope.txt")),
                             os.path.join(d, "nope.txt"))

    def test_get_real_path_encode_first(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "real.txt")
            with open(fpath, "w") as fp:
                fp.write("x")
            self.assertEqual(fsutil.get_real_path_encode_first(fpath), fpath)
            # nonexistent -> original
            self.assertEqual(
                fsutil.get_real_path_encode_first(os.path.join(d, "nope.txt")),
                os.path.join(d, "nope.txt"))

    def test_is_parent_dir(self):
        self.assertTrue(fsutil.is_parent_dir("/test/", "/test/child.txt"))
        self.assertTrue(fsutil.is_parent_dir("/test", "/test/child.txt"))
        self.assertTrue(fsutil.is_parent_dir("/test", "/test/child/grandchild.txt"))
        self.assertFalse(fsutil.is_parent_dir("/test", "/test_1/child.txt"))
        self.assertFalse(fsutil.is_parent_dir("/test", "/a/test/child.txt"))
        self.assertTrue(fsutil.is_parent_dir("/test", "/test"))

    def test_get_relative_path(self):
        self.assertEqual(
            fsutil.get_relative_path("/users/xxx/test/hello.html", "/users/xxx"),
            "test/hello.html")
        self.assertEqual(
            fsutil.get_relative_path("/tmp/test.html", "/tmp/test.html"), "")

    def test_path_equals(self):
        self.assertTrue(fsutil.path_equals("/home/a.txt", "/home/ccc/../a.txt"))

    def test_split_path_to_objects(self):
        objs = fsutil.split_path_to_objects("/a/b/c.txt")
        self.assertTrue(len(objs) > 0)
        for o in objs:
            self.assertIsInstance(o, fsutil.FileItem)
        # alias
        self.assertEqual(len(fsutil.splitpath("/a/b")),
                         len(fsutil.split_path_to_objects("/a/b")))

    def test_fixed_dir_path(self):
        self.assertEqual(fsutil.fixed_dir_path("a"), "a/")
        self.assertEqual(fsutil.fixed_dir_path("a/"), "a/")

    def test_fixed_basename(self):
        self.assertEqual(fsutil.fixed_basename("/a/b/"), "b")
        self.assertEqual(fsutil.fixed_basename("/a/b"), "b")

    def test_normalize_path(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(fsutil.normalize_path(d).endswith("/"))
            fpath = os.path.join(d, "f.txt")
            with open(fpath, "w") as fp:
                fp.write("x")
            self.assertFalse(fsutil.normalize_path(fpath).endswith("/"))

    def test_try_listdir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(fsutil.try_listdir(d), [])
            self.assertEqual(fsutil.try_listdir("/no/such/dir/xyz"), [])

    def test_is_same_file(self):
        self.assertTrue(fsutil.is_same_file("/a/x", "/a/./x"))
        self.assertFalse(fsutil.is_same_file("/a/x", "/a/y"))


class TestFsutilEncoding(unittest.TestCase):

    def test_detect_encoding(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "u.txt")
            with open(fpath, "w", encoding="utf-8") as fp:
                fp.write("hello 中文")
            self.assertEqual(fsutil.detect_encoding(fpath), "utf-8")
            # nonexistent file raises
            with self.assertRaises(Exception):
                fsutil.detect_encoding("/no/such/file", "ascii")

    def test_get_file_ext(self):
        self.assertEqual(fsutil.get_file_ext("a.png"), "png")
        self.assertEqual(fsutil.get_file_ext("a.tar.gz"), "gz")
        self.assertEqual(fsutil.get_file_ext("a"), "")
        self.assertEqual(fsutil.get_file_ext("a.verylongext"), "")

    def test_decode_encode_name(self):
        enc = fsutil.encode_name("hello.txt")
        self.assertTrue(enc.endswith(".x0"))
        self.assertEqual(fsutil.decode_name(enc), "hello.txt")
        # already encoded ext pass through
        self.assertEqual(fsutil.encode_name("x.x0"), "x.x0")
        # normal name decode falls back to unquote
        self.assertEqual(fsutil.decode_name("normal.txt"), "normal.txt")

    def test_get_safe_file_name(self):
        self.assertEqual(fsutil.get_safe_file_name("a b:c"), "a_b_c")


class TestFsutilSize(unittest.TestCase):

    def test_format_size(self):
        self.assertEqual(fsutil.format_size(10240), "10.00K")
        self.assertEqual(fsutil.format_size(1429365116108), "1.30T")
        self.assertEqual(fsutil.format_size(1024 ** 5 + 10), "1.00P")
        self.assertEqual(fsutil.format_size(-10240), "-10.00K")
        self.assertEqual(fsutil.format_size(500), "500B")
        self.assertEqual(fsutil.format_size(1024**2 + 10), "1.00M")
        self.assertEqual(fsutil.format_size(1024**3 + 10), "1.00G")
        self.assertEqual(fsutil.format_size(1024**4 + 10), "1.00T")
        self.assertEqual(fsutil.format_size(1024**5 + 10), "1.00P")

    def test_get_file_size_int(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.txt")
            with open(fpath, "w") as fp:
                fp.write("abcdef")  # 6 bytes
            self.assertEqual(fsutil.get_file_size_int(fpath), 6)
            self.assertEqual(fsutil.get_file_size_int("/no/such/file"), -1)
            with self.assertRaises(OSError):
                fsutil.get_file_size_int("/no/such/file", raise_exception=True)

    def test_get_file_size(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.txt")
            with open(fpath, "w") as fp:
                fp.write("abcdef")
            self.assertEqual(fsutil.get_file_size(fpath), 6)
            self.assertEqual(fsutil.get_file_size(fpath, format=True), "6B")
            self.assertEqual(fsutil.get_file_size("/no/such", format=True), "-")


class TestFsutilReadWrite(unittest.TestCase):

    def test_writefile_readfile(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "sub", "f.txt")
            fsutil.writefile(fpath, "hello 中文")
            self.assertEqual(fsutil.readfile(fpath), "hello 中文")
            self.assertEqual(fsutil.read(fpath), "hello 中文")
            self.assertEqual(fsutil.read_utf8(fpath), "hello 中文")
            # limit
            self.assertEqual(fsutil.readfile(fpath, limit=5), "hello")
            # bytes content
            fsutil.writefile(fpath, b"rawbytes")
            self.assertEqual(fsutil.readfile(fpath), "rawbytes")
            # aliases
            fsutil.savefile(fpath, "x")
            fsutil.savetofile(fpath, "y")
            fsutil.writebytes(fpath, b"z")
            self.assertEqual(fsutil.readfile(fpath), "z")

    def test_writeline(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.txt")
            fsutil.writeline(fpath, "line1")
            self.assertEqual(fsutil.readfile(fpath), "line1\n")

    def test_readlines(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.txt")
            with open(fpath, "w", encoding="utf-8") as fp:
                fp.write("a\nb\nc\n")
            self.assertEqual(fsutil.readlines(fpath), ["a\n", "b\n", "c\n"])
            self.assertEqual(fsutil.readlines(fpath, limit=2), ["a\n", "b\n"])

    def test_readbytes(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.bin")
            with open(fpath, "wb") as fp:
                fp.write(b"\x00\x01")
            self.assertEqual(fsutil.readbytes(fpath), b"\x00\x01")

    def test_copy(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "src.bin")
            dst = os.path.join(d, "dst.bin")
            with open(src, "wb") as fp:
                fp.write(b"abcdef" * 100)
            fsutil.copy(src, dst)
            with open(dst, "rb") as fp:
                self.assertEqual(fp.read(), b"abcdef" * 100)

    def test_touch(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "new.txt")
            fsutil.touch(fpath)
            self.assertTrue(os.path.exists(fpath))
            # existing file updates mtime
            old = os.path.getmtime(fpath)
            import time as _time
            _time.sleep(0.01)
            fsutil.touch(fpath)
            self.assertNotEqual(os.path.getmtime(fpath), old)


class TestFsutilList(unittest.TestCase):

    def test_list_files(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.txt"), "w").close()
            open(os.path.join(d, "b.txt"), "w").close()
            items = fsutil.list_files(d)
            names = sorted(item.name for item in items)
            self.assertEqual(names, ["a.txt", "b.txt"])
            self.assertEqual(fsutil.list_files(d), items)  # alias

    def test_get_display_name(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "hello world.txt")
            self.assertEqual(fsutil.get_display_name(fpath, d),
                             "hello world.txt")

    def test_listdir_abs(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.txt"), "w").close()
            # recursive (no subdirs)
            self.assertEqual(fsutil.listdir_abs(d),
                             fsutil.do_list_dir_abs_recursive(d))
            # non-recursive
            res = fsutil.listdir_abs(d, recursive=False)
            self.assertEqual(len(res), 1)

    def test_split_path_with_webpath_needs_xconfig(self):
        # list_file_objects with webpath needs xconfig.UPLOAD_DIR; ensure
        # it at least works without webpath in a temp dir
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "x.txt"), "w").close()
            items = fsutil.list_file_objects(d)
            self.assertEqual(len(items), 1)


class TestFsutilSearch(unittest.TestCase):

    def test_search_path(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "match.txt"), "w").close()
            sub = os.path.join(d, "subdir")
            os.makedirs(sub)
            open(os.path.join(sub, "match2.txt"), "w").close()
            open(os.path.join(d, "other.log"), "w").close()
            res = fsutil.search_path(d, "match*")
            self.assertEqual(len(res), 2)
            # option="file" excludes directories
            res_file = fsutil.search_path(d, "*", option="file")
            self.assertEqual(len(res_file), 3)
            # default option includes both files and dirs
            res_all = fsutil.search_path(d, "*")
            self.assertEqual(len(res_all), 4)

    def test_search_path0(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.txt"), "w").close()
            self.assertEqual(len(fsutil._search_path0(d, "a*")), 1)
            self.assertEqual(fsutil._search_path0(d, "x*"), [])


class TestFsutilConfigLoad(unittest.TestCase):

    def _write(self, d, name, content):
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(content)
        return path

    def test_parse_line(self):
        self.assertIsNone(fsutil._parse_line(""))
        self.assertIsNone(fsutil._parse_line("# comment"))
        self.assertEqual(fsutil._parse_line("  value  "), "value")

    def test_load_list_config(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "list.txt", "a\n# b\nc\n\n")
            self.assertEqual(fsutil.load_list_config(p), ["a", "c"])

    def test_load_set_config(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "set.txt", "a\nb\na\n")
            self.assertEqual(fsutil.load_set_config(p), {"a", "b"})

    def test_load_prop_config(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "x.prop", "k1=v1\nk2=v2\n")
            self.assertEqual(fsutil.load_prop_config(p)["k1"], "v1")

    def test_load_json_config(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "x.json", '{"a":1}')
            self.assertEqual(fsutil.load_json_config(p), {"a": 1})
            self.assertEqual(fsutil.load_json_dict(p)["a"], 1)

    def test_load_ini_config(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "x.ini",
                            "[s1]\nkey1=val1\nkey2=val2\n")
            result = fsutil.load_ini_config(p)
            self.assertEqual(result.sections, ["s1"])
            self.assertEqual(getattr(result.items.s1, "key1"), "val1")
            self.assertEqual(getattr(result.items.s1, "key2"), "val2")


class TestFsutilNameHelpers(unittest.TestCase):

    def test_tmp_path(self):
        path = fsutil.get_tmp_path(fname="myfile.tmp")
        self.assertTrue(path.endswith("myfile.tmp"))
        # invalid ext
        with self.assertRaises(Exception):
            fsutil.get_tmp_path(ext="tmp")
        # generated
        g = fsutil.get_tmp_path(prefix="pre_", ext=".gen")
        self.assertIn("pre_", g)
        self.assertTrue(g.endswith(".gen"))
        # alias
        self.assertEqual(fsutil.tmp_path, fsutil.get_tmp_path)

    def test_data_path(self):
        fsutil.FileUtilConfig.data_dir = "/data"
        try:
            self.assertEqual(fsutil.data_path("a.txt"),
                             os.path.join("/data", "a.txt"))
        finally:
            fsutil.FileUtilConfig.data_dir = ""

    def test_get_text_ext(self):
        # get_text_ext() returns the configured list, which may be a
        # list or a set depending on how xutils was initialized
        self.assertIsInstance(fsutil.get_text_ext(), (list, set, frozenset))


class TestFsutilFileType(unittest.TestCase):

    def test_file_type_checks(self):
        # The FS_*_EXT_LIST globals depend on how xutils was initialized,
        # so pin them explicitly to make this test order-independent.
        saved = (xutils.FS_IMG_EXT_LIST, xutils.FS_TEXT_EXT_LIST,
                 xutils.FS_AUDIO_EXT_LIST, xutils.FS_CODE_EXT_LIST)
        try:
            xutils.FS_IMG_EXT_LIST = set([".png"])
            xutils.FS_TEXT_EXT_LIST = set([".txt"])
            xutils.FS_AUDIO_EXT_LIST = set([".mp3"])
            xutils.FS_CODE_EXT_LIST = set([".py"])
            self.assertTrue(fsutil.is_img_file("a.png"))
            self.assertFalse(fsutil.is_img_file("a.txt"))
            self.assertTrue(fsutil.is_text_file("a.txt"))
            self.assertTrue(fsutil.is_audio_file("a.mp3"))
            self.assertTrue(fsutil.is_code_file("a.py"))
            self.assertTrue(fsutil.is_editable("a.py"))
            self.assertFalse(fsutil.is_editable("a.bin"))
            # is_zip_file uses its own config list -> True for .zip
            self.assertTrue(fsutil.is_zip_file("a.zip"))
            self.assertFalse(fsutil.is_zip_file("a.txt"))
        finally:
            (xutils.FS_IMG_EXT_LIST, xutils.FS_TEXT_EXT_LIST,
             xutils.FS_AUDIO_EXT_LIST, xutils.FS_CODE_EXT_LIST) = saved


class TestFsutilFileItem(unittest.TestCase):

    def test_file_item_file(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.txt")
            with open(fpath, "w") as fp:
                fp.write("hello")
            item = fsutil.FileItem(fpath)
            self.assertEqual(item.type, "file")
            self.assertEqual(item.name, "f.txt")
            self.assertTrue(hasattr(item, "path_b64"))
            self.assertTrue(hasattr(item, "encoded_path"))

    def test_file_item_dir(self):
        with tempfile.TemporaryDirectory() as d:
            item = fsutil.FileItem(d)
            self.assertEqual(item.type, "dir")
            self.assertTrue(item.path.endswith("/"))

    def test_file_item_parent_and_name(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.txt")
            with open(fpath, "w") as fp:
                fp.write("x")
            item = fsutil.FileItem(fpath, parent=d)
            self.assertEqual(item.name, "f.txt")
            item2 = fsutil.FileItem(fpath, name="custom")
            self.assertEqual(item2.name, "custom")

    def test_file_item_merge_single_child_dir(self):
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "onlychild")
            os.makedirs(sub)
            # directory with exactly one child dir
            child = os.path.join(sub, "inner")
            os.makedirs(child)
            item = fsutil.FileItem(sub, merge=True)
            # note: FileItem uses string size so the merge branch is not
            # triggered; it remains a directory item
            self.assertEqual(item.type, "dir")
            self.assertTrue(item.path.endswith("/"))

    def test_file_item_lt(self):
        a = fsutil.FileItem.__new__(fsutil.FileItem)
        a.type = "dir"
        a.name = "a"
        b = fsutil.FileItem.__new__(fsutil.FileItem)
        b.type = "file"
        b.name = "b"
        self.assertTrue(a < b)
        self.assertFalse(b < a)
        c = fsutil.FileItem.__new__(fsutil.FileItem)
        c.type = "file"
        c.name = "a"
        d = fsutil.FileItem.__new__(fsutil.FileItem)
        d.type = "file"
        d.name = "b"
        self.assertTrue(c < d)

    def test_file_stat_info(self):
        info = fsutil.FileStatInfo()
        self.assertEqual(info.st_size, 0)


class TestFsutilMove(unittest.TestCase):

    def test_move_not_exists(self):
        self.assertIsNone(fsutil.MoveFileHandler.move("/no/such/src", "/no/dst"))

    def test_move_simple(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "src.txt")
            dst = os.path.join(d, "dst.txt")
            with open(src, "w") as fp:
                fp.write("x")
            fsutil.MoveFileHandler.move(src, dst)
            self.assertTrue(os.path.exists(dst))
            self.assertFalse(os.path.exists(src))
            self.assertEqual(fsutil.rename_file(dst, dst + "2"),
                             fsutil.mvfile(dst, dst + "2"))

    def test_move_rename_on_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "src.txt")
            dst = os.path.join(d, "dst.txt")
            with open(src, "w") as fp:
                fp.write("x")
            with open(dst, "w") as fp:
                fp.write("y")
            # find_target_path
            target = fsutil.MoveFileHandler.find_target_path(dst)
            self.assertFalse(os.path.exists(target))
            fsutil.MoveFileHandler.move(src, dst, rename_on_conflict=True)
            self.assertTrue(os.path.exists(dst))

    def test_find_target_path_exhausted(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "x")
            for i in range(1, 11):
                open("%s-%s" % (base, i), "w").close()
            with self.assertRaises(Exception):
                fsutil.MoveFileHandler.find_target_path(base + ".txt")


class TestFsutilDelete(unittest.TestCase):

    def setUp(self):
        self._trash = fsutil.FileUtilConfig.trash_dir
        self._data = fsutil.FileUtilConfig.data_dir
        self.tmp = tempfile.TemporaryDirectory()
        fsutil.FileUtilConfig.trash_dir = os.path.join(self.tmp.name, "trash")
        os.makedirs(fsutil.FileUtilConfig.trash_dir)

    def tearDown(self):
        fsutil.FileUtilConfig.trash_dir = self._trash
        fsutil.FileUtilConfig.data_dir = self._data
        self.tmp.cleanup()

    def test_remove_file_not_exists(self):
        self.assertFalse(fsutil.remove_file("/no/such/file"))
        self.assertFalse(fsutil.rmfile("/no/such/file"))
        self.assertFalse(fsutil.remove("/no/such/file"))
        self.assertFalse(fsutil.delete_file("/no/such/file"))

    def test_remove_file_hard(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.txt")
            with open(fpath, "w") as fp:
                fp.write("x")
            self.assertTrue(fsutil.remove_file(fpath, hard=True))
            self.assertFalse(os.path.exists(fpath))

    def test_remove_file_soft(self):
        d = self.tmp.name
        fpath = os.path.join(d, "f.txt")
        with open(fpath, "w") as fp:
            fp.write("x")
        self.assertTrue(fsutil.remove_file(fpath, hard=False))
        self.assertFalse(os.path.exists(fpath))
        # moved into trash
        self.assertTrue(os.path.exists(fsutil.FileUtilConfig.trash_dir))

    def test_remove_link(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "target.txt")
            link = os.path.join(d, "link.txt")
            with open(target, "w") as fp:
                fp.write("x")
            try:
                os.symlink(target, link)
            except OSError:
                self.skipTest("symlink not supported on this platform")
            if os.path.islink(link):
                self.assertTrue(fsutil.remove_file(link))
                self.assertFalse(os.path.exists(link))

    def test_rmdir_hard(self):
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "sub")
            os.makedirs(sub)
            fsutil.rmdir(sub, hard=True)
            self.assertFalse(os.path.exists(sub))

    def test_rmdir_soft(self):
        d = self.tmp.name
        sub = os.path.join(d, "sub")
        os.makedirs(sub)
        fsutil.rmdir(sub, hard=False)
        self.assertFalse(os.path.exists(sub))

    def test_rmdir_already_in_trash(self):
        # create a dir inside trash; rmdir should remove directly
        inside = os.path.join(fsutil.FileUtilConfig.trash_dir, "inside")
        os.makedirs(inside)
        fsutil.rmdir(inside, hard=False)
        self.assertFalse(os.path.exists(inside))

    def test_remove_file_dir(self):
        d = self.tmp.name
        sub = os.path.join(d, "sub")
        os.makedirs(sub)
        self.assertTrue(fsutil.remove_file(sub))
        self.assertFalse(os.path.exists(sub))


class TestFsutilBackup(unittest.TestCase):

    def test_backupfile(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "f.txt")
            with open(src, "w") as fp:
                fp.write("x")
            fsutil.backupfile(src)
            self.assertTrue(os.path.exists(src + ".bak"))
            # custom backup dir
            bdir = os.path.join(d, "bak")
            os.makedirs(bdir)
            fsutil.backupfile(src, backup_dir=bdir)
            self.assertTrue(os.path.exists(os.path.join(bdir, "f.txt.bak")))


class TestFsutilWebpath(unittest.TestCase):

    def setUp(self):
        self._data = fsutil.FileUtilConfig.data_dir
        self.tmp = tempfile.TemporaryDirectory()
        fsutil.FileUtilConfig.data_dir = self.tmp.name

    def tearDown(self):
        fsutil.FileUtilConfig.data_dir = self._data
        self.tmp.cleanup()

    def test_get_webpath(self):
        fpath = os.path.join(self.tmp.name, "a.txt")
        with open(fpath, "w") as fp:
            fp.write("x")
        self.assertEqual(fsutil.get_webpath(fpath), "/data/a.txt")
        self.assertEqual(fsutil.get_safe_webpath(fpath), "/data/a.txt")

    def test_get_webpath_outside(self):
        # file outside data dir -> /fs/~ form; unsafe path raises
        outside = os.path.abspath("/etc/passwd")
        self.assertTrue(fsutil.get_webpath(outside).startswith("/fs/~"))
        with self.assertRaises(Exception):
            fsutil.get_safe_webpath(outside)


class TestFsutilFreeSpace(unittest.TestCase):

    def test_get_free_space(self):
        with tempfile.TemporaryDirectory() as d:
            space = fsutil.get_free_space(d)
            self.assertIsInstance(space, int)
            self.assertGreaterEqual(space, 0)


class TestFsutilHasher(unittest.TestCase):

    def test_get_hash_algo(self):
        h = fsutil.FileHasher("x", hash_type="md5")
        self.assertEqual(h.get_hash_algo().name, "md5")
        h.hash_type = "sha1"
        self.assertEqual(h.get_hash_algo().name, "sha1")
        h.hash_type = "sha256"
        self.assertEqual(h.get_hash_algo().name, "sha256")
        h.hash_type = "sha512"
        self.assertEqual(h.get_hash_algo().name, "sha512")
        h.hash_type = "xx"
        with self.assertRaises(Exception):
            h.get_hash_algo()

    def test_get_hash_hex(self):
        with tempfile.TemporaryDirectory() as d:
            fpath = os.path.join(d, "f.txt")
            with open(fpath, "w", encoding="utf-8") as fp:
                fp.write("abc")
            # md5("abc") known
            self.assertEqual(fsutil.get_md5_sum(fpath),
                             "900150983cd24fb0d6963f7d28e17f72")
            self.assertEqual(fsutil.get_sha1_sum(fpath),
                             "a9993e364706816aba3e25717850c26c9cd0d89d")
            self.assertEqual(
                fsutil.get_sha256_sum(fpath),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
            # empty file path -> ""
            self.assertEqual(fsutil.get_md5_sum("/no/such/file"), "")
            # directory -> ""
            self.assertEqual(fsutil.get_md5_sum(d), "")
            # hash of empty content
            empty = os.path.join(d, "empty.txt")
            open(empty, "w").close()
            self.assertEqual(fsutil.get_md5_sum(empty),
                             "d41d8cd98f00b204e9800998ecf8427e")


if __name__ == "__main__":
    unittest.main()
