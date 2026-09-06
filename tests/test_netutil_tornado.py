# -*- coding: utf-8 -*-
"""Coverage tests for xutils.netutil, xutils.tornado.util, xutils.tornado.escape.

These are pure-function / safe-to-test units. No real network calls are made.
"""

import datetime
import os

import pytest

from xutils import netutil
from xutils.tornado import util as tutil
from xutils.tornado import escape as tescape


# ---------------------------------------------------------------------------
# xutils.netutil  -- pure helpers
# ---------------------------------------------------------------------------

class TestNetMock:

    def test_set_and_reset(self):
        assert netutil._mock is None
        mock = netutil.NetworkMock()
        netutil.set_net_mock(mock)
        assert netutil._mock is mock
        netutil.set_net_mock(None)
        assert netutil._mock is None

    def test_network_mock_interface_raises(self):
        mock = netutil.NetworkMock()
        with pytest.raises(NotImplementedError):
            mock.http_get("http://x", None, None)
        with pytest.raises(NotImplementedError):
            mock.http_post("http://x", "", "utf-8")


class TestSplithost:

    def test_docstring_cases(self):
        assert netutil.splithost('//host[:port]/path') == ('host[:port]', '/path')
        assert netutil.splithost('http://www.baidu.com/index.html') == ('www.baidu.com', '/index.html')

    def test_no_match(self):
        # a string that does not match the pattern returns None + full url
        assert netutil.splithost('') == ('', '')


class TestJoinWebPath:

    def test_strip_leading_slash(self):
        result = netutil.join_web_path('/root', '/a/b')
        assert result.endswith(os.path.join('root', 'a', 'b'))

    def test_no_leading_slash(self):
        result = netutil.join_web_path('/root', 'a/b')
        assert result.endswith(os.path.join('root', 'a', 'b'))

    def test_empty_webpath(self):
        result = netutil.join_web_path('/root', '')
        assert result == os.path.join('/root', '')


class TestHttpHomeAndUrl:

    def test_get_http_home_plain(self):
        assert netutil.get_http_home("www.xnote.com") == 'http://www.xnote.com'

    def test_get_http_home_https(self):
        assert netutil.get_http_home("https://www.xnote.com") == 'https://www.xnote.com'

    def test_get_http_home_none_raises(self):
        with pytest.raises(AssertionError):
            netutil.get_http_home(None)

    def test_get_http_url_adds_scheme(self):
        assert netutil.get_http_url("www.xnote.com/path") == 'http://www.xnote.com/path'

    def test_get_http_url_strips_fragment(self):
        assert netutil.get_http_url("http://x.com/p#frag") == 'http://x.com/p'

    def test_get_http_url_keeps_scheme(self):
        assert netutil.get_http_url("https://x.com/p") == 'https://x.com/p'


class TestIsHttpUrl:

    def test_non_str(self):
        assert netutil.is_http_url(None) is False
        assert netutil.is_http_url(123) is False

    def test_not_http(self):
        assert netutil.is_http_url("ftp://x") is False
        assert netutil.is_http_url("/relative") is False

    def test_http_and_https(self):
        assert netutil.is_http_url("http://x") is True
        assert netutil.is_http_url("https://x") is True


class TestGetHostByUrl:

    def test_match(self):
        assert netutil.get_host_by_url("http://www.baidu.com/index.html") == 'www.baidu.com'

    def test_https_match(self):
        assert netutil.get_host_by_url("https://x.com:8080/a") == 'x.com:8080'

    def test_no_match(self):
        assert netutil.get_host_by_url("/relative/path") is None

    def test_get_host_alias(self):
        assert netutil.get_host("http://x.com") == 'x.com'


class TestHttpResource:

    def test_init_attrs(self):
        r = netutil.HttpResource("http://www.a.com/a/b")
        assert r.url == 'http://www.a.com/a/b'
        assert r.protocol == 'http'
        assert r.domain == 'www.a.com'

    def test_get_res_url_full_http(self):
        r = netutil.HttpResource("http://www.a.com")
        assert r.get_res_url("https://b.com/b.png") == 'https://b.com/b.png'

    def test_get_res_url_double_slash(self):
        r = netutil.HttpResource("http://www.a.com")
        assert r.get_res_url("//b.com/b.png") == 'http://b.com/b.png'

    def test_get_res_url_absolute_path(self):
        r = netutil.HttpResource("http://www.a.com")
        assert r.get_res_url("/b.png") == 'http://www.a.com/b.png'

    def test_get_res_url_relative(self):
        r = netutil.HttpResource("http://www.a.com/a")
        assert r.get_res_url("b.png") == 'http://www.a.com/a/b.png'

    def test_get_res_url_none(self):
        r = netutil.HttpResource("http://www.a.com")
        assert r.get_res_url("") is None
        assert r.get_res_url(None) is None

    def test_get_res_returns_resource(self):
        r = netutil.HttpResource("http://www.a.com")
        sub = r.get_res("b.png")
        assert isinstance(sub, netutil.HttpResource)

    def test_get_uses_mock(self):
        class M(netutil.NetworkMock):
            def http_get(self, url, charset, params):
                return "mocked:" + url

        netutil.set_net_mock(M())
        try:
            r = netutil.HttpResource("http://www.a.com/page")
            assert r.get() == "mocked:http://www.a.com/page"
        finally:
            netutil.set_net_mock(None)


class TestHttpExceptions:

    def test_http_error_attrs(self):
        e = netutil.HttpError(404, "not found")
        assert e.status == 404
        assert str(e) == "not found"

    def test_file_not_found_subclass(self):
        e = netutil.HttpFileNotFoundError(404, "missing")
        assert isinstance(e, netutil.HttpError)
        assert e.status == 404

    def test_http_response_attrs(self):
        r = netutil.HttpResponse(200, {"k": "v"}, "body")
        assert r.status == 200
        assert r.headers == {"k": "v"}
        assert r.content == "body"


class TestBuildQueryString:

    def test_basic(self):
        qs = netutil.build_query_string({"a": "1", "b": "2"})
        assert qs == "a=1&b=2"

    def test_quoting(self):
        qs = netutil.build_query_string({"q": "a b"})
        assert qs == "q=a%20b"

    def test_skip_empty_value_true(self):
        qs = netutil.build_query_string({"a": "", "b": None, "c": "x"}, skip_empty_value=True)
        assert qs == "c=x"

    def test_skip_empty_value_false(self):
        qs = netutil.build_query_string({"a": ""}, skip_empty_value=False)
        assert qs == "a="


class TestJoinUrlAndParams:

    def test_none_params(self):
        assert netutil._join_url_and_params("http://x/p", None) == "http://x/p"

    def test_no_question(self):
        assert netutil._join_url_and_params("http://x/p", {"a": "1"}) == "http://x/p?a=1"

    def test_with_question(self):
        assert netutil._join_url_and_params("http://x/p?z=2", {"a": "1"}) == "http://x/p?z=2&a=1"

    def test_skip_empty_value(self):
        # empty value is skipped, so query string is empty and a trailing "?" is appended
        assert netutil._join_url_and_params("http://x/p", {"a": ""}, skip_empty_value=True) == "http://x/p?"


class TestHttpGetPostMock:

    def test_http_get_mock(self):
        class M(netutil.NetworkMock):
            def http_get(self, url, charset, params):
                assert url == "http://x/p?a=1"
                return "GET-" + url

        netutil.set_net_mock(M())
        try:
            assert netutil.http_get("http://x/p", params={"a": "1"}) == "GET-http://x/p?a=1"
        finally:
            netutil.set_net_mock(None)

    def test_http_post_mock(self):
        class M(netutil.NetworkMock):
            def http_post(self, url, data, charset):
                return "POST-" + data

        netutil.set_net_mock(M())
        try:
            assert netutil.http_post("http://x/p", "body") == "POST-body"
        finally:
            netutil.set_net_mock(None)


class TestGetFileExtByContentType:

    def test_known_types(self):
        assert netutil.get_file_ext_by_content_type("image/png") == ".png"
        assert netutil.get_file_ext_by_content_type("image/jpg") == ".jpg"
        assert netutil.get_file_ext_by_content_type("image/jpeg") == ".jpeg"
        assert netutil.get_file_ext_by_content_type("image/gif") == ".gif"
        assert netutil.get_file_ext_by_content_type("image/webp") == ".webp"
        assert netutil.get_file_ext_by_content_type("image/svg+xml") == ".svg"

    def test_unknown_returns_none(self):
        assert netutil.get_file_ext_by_content_type("text/html") is None
        assert netutil.get_file_ext_by_content_type(None) is None


class TestStructURL:

    def test_get_single_param_list(self):
        s = netutil.StructURL()
        s.params = {"a": ["1", "2"], "b": []}
        assert s.get_single_param("a") == "1"
        assert s.get_single_param("b") is None
        assert s.get_single_param("missing") is None

    def test_get_single_param_default_name(self):
        s = netutil.StructURL()
        s.params = {"": ["x"]}
        assert s.get_single_param() == "x"

    def test_get_list_param(self):
        s = netutil.StructURL()
        s.params = {"a": ["1", "2"]}
        assert s.get_list_param("a") == ["1", "2"]
        assert s.get_list_param("missing") == []

    def test_to_url_no_params(self):
        s = netutil.StructURL()
        s.path = "/p"
        assert s.to_url() == "/p"

    def test_to_url_with_params(self):
        s = netutil.StructURL()
        s.path = "/p"
        s.params = {"a": ["1"], "b": ["2", "3"]}
        assert s.to_url() == "/p?a=1&b=2&b=3"


class TestDecodeRespBytes:

    def test_plain(self):
        assert netutil._decode_resp_bytes(b"hello", "utf-8") == "hello"

    def test_gzip(self):
        import gzip
        import io
        data = b"hello gzip"
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write(data)
        compressed = buf.getvalue()
        assert netutil._decode_resp_bytes(compressed, "utf-8", "gzip") == "hello gzip"

    def test_unsupported_encoding(self):
        with pytest.raises(Exception):
            netutil._decode_resp_bytes(b"x", "utf-8", "br")


class TestParseUrl:

    def test_with_query(self):
        r = netutil.parse_url("http://x/p?a=1&b=2")
        assert r.path == "http://x/p"
        assert r.params["a"] == ["1"]
        assert r.params["b"] == ["2"]

    def test_no_query(self):
        # no '?' present -> path stays empty, query part parsed (here yields no params)
        r = netutil.parse_url("http://x/p")
        assert r.path == ""
        assert r.params == {}

    def test_empty_url(self):
        r = netutil.parse_url()
        assert r.path == ""
        assert r.params == {}


# ---------------------------------------------------------------------------
# xutils.tornado.util
# ---------------------------------------------------------------------------

class TestObjectDict:

    def test_getattr_and_setattr(self):
        d = tutil.ObjectDict()
        d["key"] = "value"
        assert d.key == "value"
        d.foo = "bar"
        assert d["foo"] == "bar"

    def test_missing_attr_raises(self):
        d = tutil.ObjectDict()
        with pytest.raises(AttributeError):
            _ = d.missing


class TestGzipDecompressor:

    def test_roundtrip(self):
        import gzip
        import io
        data = b"hello world" * 10
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write(data)
        compressed = buf.getvalue()

        d = tutil.GzipDecompressor()
        out = d.decompress(compressed)
        out += d.flush()
        assert out == data

    def test_unconsumed_tail(self):
        d = tutil.GzipDecompressor()
        assert d.unconsumed_tail == b""


class TestSimpleHelpers:

    def test_u(self):
        assert tutil.u("abc") == "abc"

    def test_type_aliases(self):
        assert tutil.unicode_type is str
        assert tutil.basestring_type is str
        assert tutil.bytes_type is bytes


class TestImportObject:

    def test_import_module(self):
        obj = tutil.import_object("xutils.tornado.escape")
        assert obj is tescape

    def test_import_subattr(self):
        obj = tutil.import_object("xutils.tornado.escape.xhtml_escape")
        assert obj is tescape.xhtml_escape

    def test_missing_leaf_raises(self):
        with pytest.raises(ImportError):
            tutil.import_object("xutils.tornado.escape.nonexistent_attr")

    def test_missing_module_raises(self):
        with pytest.raises(ImportError):
            tutil.import_object("xutils.tornado.escape.nonexistent_module.leaf")


class TestErrnoFromException:

    def test_has_errno(self):
        e = ValueError()
        e.errno = 42
        assert tutil.errno_from_exception(e) == 42

    def test_has_args(self):
        e = ValueError("boom", 7)
        assert tutil.errno_from_exception(e) == "boom"

    def test_no_args(self):
        e = ValueError()
        assert tutil.errno_from_exception(e) is None


class TestArgReplacer:

    def test_positional_get_and_replace(self):
        def func(a, name):
            return a, name

        repl = tutil.ArgReplacer(func, "name")
        assert repl.arg_pos is not None
        assert repl.get_old_value(("a", "old"), {}) == "old"
        old, args, kwargs = repl.replace("new", ("a", "old"), {})
        assert old == "old"
        assert args[1] == "new"

    def test_keyword_get_and_replace(self):
        def func(a, name="default"):
            return a, name

        repl = tutil.ArgReplacer(func, "name")
        assert repl.get_old_value(("a",), {"name": "kw"}) == "kw"
        old, args, kwargs = repl.replace("new", ("a",), {"name": "kw"})
        assert old == "kw"
        assert kwargs["name"] == "new"

    def test_not_positional_param(self):
        def func(a, b):
            return a, b

        repl = tutil.ArgReplacer(func, "name")
        assert repl.arg_pos is None
        # get_old_value falls back to kwargs
        assert repl.get_old_value(("a", "b"), {"name": "x"}) == "x"
        old, args, kwargs = repl.replace("new", ("a", "b"), {})
        assert old is None
        assert kwargs["name"] == "new"


class TestTimedeltaToSeconds:

    def test_basic(self):
        td = datetime.timedelta(days=1, seconds=1, microseconds=1)
        assert tutil.timedelta_to_seconds(td) == pytest.approx(86401.000001)


class TestWebsocketMask:

    def test_mask_python(self):
        mask = b"\x01\x02\x03\x04"
        data = b"abcdefgh"
        out = tutil._websocket_mask_python(mask, data)
        # mask twice -> original
        again = tutil._websocket_mask_python(mask, out)
        assert again == data

    def test_mask_unknown(self):
        mask = b"\x00\x00\x00\x00"
        data = b"hello"
        assert tutil._websocket_mask_python(mask, data) == data


class TestConfigurable:

    class Base(tutil.Configurable):
        @classmethod
        def configurable_base(cls):
            return TestConfigurable.Base

        @classmethod
        def configurable_default(cls):
            return TestConfigurable.ImplA

    class ImplA(Base):
        def initialize(self, value=0):
            self.value = value

    class ImplB(Base):
        def initialize(self, value=0):
            self.value = value

    def test_configured_class_default(self):
        cls = TestConfigurable.Base.configured_class()
        assert cls is TestConfigurable.ImplA

    def test_configure_valid_subclass(self):
        base = TestConfigurable.Base
        base.configure(TestConfigurable.ImplB)
        try:
            inst = TestConfigurable.Base(value=5)
            assert isinstance(inst, TestConfigurable.ImplB)
            assert inst.value == 5
        finally:
            base.configure(None)

    def test_configure_invalid_subclass(self):
        with pytest.raises(ValueError):
            TestConfigurable.Base.configure(object)

    def test_configurable_base_raises(self):
        class Raw(tutil.Configurable):
            pass

        with pytest.raises(NotImplementedError):
            Raw.configurable_base()
        with pytest.raises(NotImplementedError):
            Raw.configurable_default()

    def test_save_restore_configuration(self):
        base = TestConfigurable.Base
        saved = base._save_configuration()
        base.configure(TestConfigurable.ImplB)
        base._restore_configuration(saved)
        assert base.configured_class() is TestConfigurable.ImplA

    def test_instantiate_subclass_directly(self):
        # cls is not the base -> impl = cls, initialize() is called directly
        inst = TestConfigurable.ImplB(value=7)
        assert isinstance(inst, TestConfigurable.ImplB)
        assert inst.value == 7


# Module-level configurable classes so import_object() can resolve a string path
# (import_object splits on '.' and imports parts[:-1] as a *module*).
class _StrBase(tutil.Configurable):
    @classmethod
    def configurable_base(cls):
        return _StrBase

    @classmethod
    def configurable_default(cls):
        return _StrImplA


class _StrImplA(_StrBase):
    def initialize(self, value=0):
        self.value = value


class _StrImplB(_StrBase):
    def initialize(self, value=0):
        self.value = value


class TestConfigurableString:

    def test_configure_by_string(self):
        _StrBase.configure(__name__ + "._StrImplB")
        try:
            inst = _StrBase(value=9)
            assert isinstance(inst, _StrImplB)
            assert inst.value == 9
        finally:
            _StrBase.configure(None)


# ---------------------------------------------------------------------------
# xutils.tornado.escape
# ---------------------------------------------------------------------------

class TestXhtml:

    def test_escape(self):
        assert tescape.xhtml_escape("<a>&'\"" ) == "&lt;a&gt;&amp;&#39;&quot;"

    def test_unescape_named(self):
        assert tescape.xhtml_unescape("&lt;&amp;&quot;&gt;") == '<&">'
        assert tescape.xhtml_unescape("&lt;&amp;&gt;") == "<&>"

    def test_unescape_numeric_dec(self):
        assert tescape.xhtml_unescape("&#65;") == "A"

    def test_unescape_numeric_hex(self):
        assert tescape.xhtml_unescape("&#x41;") == "A"

    def test_unescape_numeric_invalid(self):
        # an invalid numeric entity falls back to original text
        assert tescape.xhtml_unescape("&#zz;") == "&#zz;"

    def test_unescape_unknown_named(self):
        assert tescape.xhtml_unescape("&zzz;") == "&zzz;"

    def test_escape_with_bytes(self):
        assert tescape.xhtml_escape(b"<") == "&lt;"


class TestJson:

    def test_encode(self):
        assert tescape.json_encode({"a": 1}) == '{"a": 1}'

    def test_encode_script_safe(self):
        assert "</" not in tescape.json_encode({"x": "</script>"})
        assert "<\\/" in tescape.json_encode({"x": "</script>"})

    def test_decode(self):
        assert tescape.json_decode('{"a": 1}') == {"a": 1}

    def test_decode_bytes(self):
        assert tescape.json_decode(b'{"a": 1}') == {"a": 1}


class TestSqueeze:

    def test_collapses_whitespace(self):
        assert tescape.squeeze("  a   b\n\tc  ") == "a b c"


class TestUrlEscape:

    def test_plus_true(self):
        assert tescape.url_escape("a b") == "a+b"

    def test_plus_false(self):
        assert tescape.url_escape("a b", plus=False) == "a%20b"

    def test_bytes_input(self):
        assert tescape.url_escape(b"a b") == "a+b"


class TestUrlUnescape:

    def test_plus_true(self):
        assert tescape.url_unescape("a+b") == "a b"

    def test_plus_false(self):
        assert tescape.url_unescape("a%20b", plus=False) == "a b"

    def test_encoding_none(self):
        out = tescape.url_unescape("a%20b", encoding=None)
        assert out == b"a b"

    def test_encoding_str(self):
        out = tescape.url_unescape("a%20b", encoding="utf-8")
        assert out == "a b"


class TestParseQsBytes:

    def test_basic(self):
        result = tescape.parse_qs_bytes("a=1&b=2")
        assert result["a"] == [b"1"]
        assert result["b"] == [b"2"]


class TestUtf8:

    def test_bytes_passthrough(self):
        assert tescape.utf8(b"abc") is b"abc"

    def test_none_passthrough(self):
        assert tescape.utf8(None) is None

    def test_str_encode(self):
        assert tescape.utf8("abc") == b"abc"

    def test_invalid_type(self):
        with pytest.raises(TypeError):
            tescape.utf8(123)


class TestToUnicode:

    def test_none(self):
        assert tescape.to_unicode(None) is None

    def test_str(self):
        assert tescape.to_unicode("abc") == "abc"

    def test_bytes(self):
        assert tescape.to_unicode(b"abc") == "abc"

    def test_invalid_type(self):
        with pytest.raises(TypeError):
            tescape.to_unicode(123)


class TestToBasestring:

    def test_str(self):
        assert tescape.to_basestring("abc") == "abc"

    def test_none(self):
        assert tescape.to_basestring(None) is None

    def test_bytes(self):
        assert tescape.to_basestring(b"abc") == "abc"

    def test_invalid_type(self):
        with pytest.raises(TypeError):
            tescape.to_basestring(123)


class TestRecursiveUnicode:

    def test_dict(self):
        out = tescape.recursive_unicode({b"a": b"1"})
        assert out == {"a": "1"}

    def test_list(self):
        assert tescape.recursive_unicode([b"a", b"b"]) == ["a", "b"]

    def test_tuple(self):
        assert tescape.recursive_unicode((b"a", b"b")) == ("a", "b")

    def test_bytes(self):
        assert tescape.recursive_unicode(b"a") == "a"

    def test_scalar(self):
        assert tescape.recursive_unicode(123) == 123

    def test_nested(self):
        out = tescape.recursive_unicode({"k": [b"x", (b"y", {b"z": b"1"})]})
        assert out == {"k": ["x", ("y", {"z": "1"})]}


class TestLinkify:

    def test_basic(self):
        out = tescape.linkify("Hello http://tornadoweb.org!")
        assert out == 'Hello <a href="http://tornadoweb.org">http://tornadoweb.org</a>!'

    def test_no_protocol(self):
        out = tescape.linkify("visit www.facebook.com today")
        assert 'href="http://www.facebook.com"' in out

    def test_extra_params_str(self):
        out = tescape.linkify("http://x.com", extra_params='rel="nofollow"')
        assert 'rel="nofollow"' in out

    def test_extra_params_callable(self):
        def cb(url):
            return 'class="ext"'
        out = tescape.linkify("http://x.com", extra_params=cb)
        assert 'class="ext"' in out

    def test_require_protocol(self):
        # www without protocol should NOT be linkified
        out = tescape.linkify("visit www.facebook.com", require_protocol=True)
        assert "href" not in out

    def test_bad_protocol(self):
        out = tescape.linkify("see javascript:alert(1)", require_protocol=True)
        # javascript not in permitted protocols
        assert "href" not in out

    def test_permitted_protocols(self):
        out = tescape.linkify("http://x.com", permitted_protocols=["ftp"])
        assert "href" not in out

    def test_shorten(self):
        long_url = "http://" + ("a" * 60) + ".com/path/segment"
        out = tescape.linkify(long_url, shorten=True)
        # shortened link produced, contains ellipsis
        assert "..." in out
        assert "title=" in out

    def test_shorten_with_amp(self):
        long_url = "http://www.example.com/" + ("x" * 40) + "?a=1&b=2&c=3"
        out = tescape.linkify(long_url, shorten=True)
        assert "..." in out

    def test_shorten_still_long(self):
        # very long path triggers the len(url) > max_len*1.5 clip branch
        long_url = "http://www.example.com/" + ("y" * 40)
        out = tescape.linkify(long_url, shorten=True)
        assert "..." in out


class TestDoctests:

    def test_doctests_returns_suite(self):
        suite = tutil.doctests()
        assert suite is not None


class TestBuildUnicodeMap:

    def test_map_is_built(self):
        # _HTML_UNICODE_MAP is populated at import; spot-check a known entity
        assert tescape._HTML_UNICODE_MAP["amp"] == "&"
        # ensure the builder function returns a dict
        m = tescape._build_unicode_map()
        assert isinstance(m, dict)
        assert m["lt"] == "<"
