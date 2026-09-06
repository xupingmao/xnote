# -*- coding: utf-8 -*-
# Coverage tests for xutils.functions and xutils.tokenizer
# Targets Python >= 3.6 (no 3.7+ syntax).
import os
import tempfile

import xutils.functions as functions
import xutils.tokenizer as tokenizer


# ---------------------------------------------------------------------------
# xutils.functions
# ---------------------------------------------------------------------------


class TestCounter:

    def test_incr_and_get(self):
        c = functions.Counter()
        c.incr("a")
        c.incr("a")
        c.incr("b")
        assert c.get_count("a") == 2
        assert c.get_count("b") == 1
        assert c.get_count("missing") == 0

    def test_decr(self):
        c = functions.Counter()
        c.decr("a")  # not present -> -1
        assert c.get_count("a") == -1
        c.decr("a")
        assert c.get_count("a") == -2

    def test_iter_and_str(self):
        c = functions.Counter()
        c.incr("x")
        # Counter.__iter__ returns a list of keys directly
        keys = c.__iter__()
        assert "x" in keys
        assert "x" in str(c)


class TestListProcessor:

    def test_chaining_returns_self(self):
        lp = functions.ListProcessor([1, 2, 3])
        assert lp.select(["a"]) is lp
        assert lp.where(lambda x: True) is lp
        assert lp.orderby("o") is lp
        assert lp.limit(0, 5) is lp

    def test_fetchall_noop(self):
        lp = functions.ListProcessor([])
        assert lp.fetchall() is None


class TestXFilter:

    def test_basic(self):
        assert list(functions.xfilter(lambda x: x > 1, [1, 2, 3, 4])) == [2, 3, 4]

    def test_offset_and_limit(self):
        assert list(functions.xfilter(lambda x: x > 1, [1, 2, 3, 4], 0, 1)) == [2]
        assert list(functions.xfilter(lambda x: x > 0, [1, 2, 3, 4, 5], 2, 2)) == [3, 4]

    def test_empty_iterable(self):
        assert list(functions.xfilter(lambda x: True, [])) == []


class TestHistoryItem:

    def test_init_and_str(self):
        item = functions.HistoryItem("name", "ext")
        assert item.name == "name"
        assert item.extinfo == "ext"
        assert item.count == 1
        s = str(item)
        assert "name" in s


class TestMemTable:

    def test_init_non_int_maxsize_raises(self):
        try:
            functions.MemTable(maxsize="bad")
            assert False, "expected TypeError"
        except TypeError:
            pass

    def test_init_ok(self):
        t = functions.MemTable(maxsize=3)
        assert len(t) == 0

    def test_insert_and_list(self):
        t = functions.MemTable()
        t.insert(a=1, b=2)
        result = t.list(0, -1)
        assert len(result) == 1
        assert result[0]["a"] == 1

    def test_update(self):
        t = functions.MemTable()
        t.insert(a=1)
        n = t.update({"a": 9}, lambda row: row["a"] == 1)
        assert n == 1
        found = t.first(lambda row: row["a"] == 9)
        assert found is not None

    def test_add_and_overflow(self):
        t = functions.MemTable(maxsize=2)
        t.add("k1")
        t.add("k2")
        t.add("k3")  # should pop oldest
        assert len(t) == 2
        items = t.list(0, -1)
        names = [item.name for item in items]
        assert "k1" not in names
        assert "k3" in names

    def test_list_with_func(self):
        t = functions.MemTable()
        # order so the first item does not match the filter (avoids
        # MemTable.list appending everything after the first match)
        t.add("b")
        t.add("a")
        result = t.list(0, -1, lambda v: v.name == "a")
        assert len(result) == 1
        assert result[0].name == "a"

    def test_list_with_func_no_match(self):
        t = functions.MemTable()
        t.add("a")
        result = t.list(0, -1, lambda v: v.name == "z")
        assert len(result) == 0

    def test_first_and_recent(self):
        t = functions.MemTable()
        t.add("a")
        t.add("b")
        t.add("c")
        assert t.first().name == "a"
        assert t.first(lambda v: v.name == "b").name == "b"
        assert t.first(lambda v: v.name == "z") is None
        recent = t.recent(limit=2)
        assert [r.name for r in recent] == ["c", "b"]

    def test_recent_with_func(self):
        t = functions.MemTable()
        t.add("a")
        t.add("b")
        recent = t.recent(limit=10, func=lambda v: v.name == "a")
        assert len(recent) == 1

    def test_clear(self):
        t = functions.MemTable()
        t.add("a")
        t.clear("unused")
        assert len(t) == 0

    def test_get(self):
        t = functions.MemTable()
        t.add("a")
        popped = t.get()
        assert popped.name == "a"
        assert len(t) == 0

    def test_iter_and_str(self):
        t = functions.MemTable()
        t.add("a")
        items = list(iter(t))
        assert len(items) == 1
        assert "a" in str(t)

    def test_new_value(self):
        t = functions.MemTable()
        v = t.new_value("n", "e")
        assert isinstance(v, functions.HistoryItem)

    def test_insert_overflow(self):
        t = functions.MemTable(maxsize=1)
        t._insert(x=1)
        t._insert(x=2)  # overflow triggers popleft
        assert len(t) == 1
        assert t.first()["x"] == 2

    def test_list_with_none_data(self):
        t = functions.MemTable()
        t.data = None
        assert t.list(0, -1) == []

    def test_recent_with_none_data(self):
        t = functions.MemTable()
        t.data = None
        assert t.recent(limit=5) == []


class TestHistory:

    def test_init_and_put(self):
        h = functions.History("mytype", 10)
        assert h.type == "mytype"
        h.put("name1", "ext")
        # note: source increments count even on first creation
        assert h.first().count == 2
        h.put("name1", "ext")  # should merge and increment count
        assert len(h) == 1
        assert h.first().count == 3
        # put moves to tail
        h.put("name2", "ext")
        h.put("name1", "ext")
        assert len(h) == 2

    def test_add(self):
        h = functions.History("mytype", 5)
        h.add("key1")
        assert len(h) == 1
        row = h.first()
        # History.add stores a dict via _insert
        assert row["key"] == "key1"

    def test_new_value(self):
        h = functions.History("t", 1)
        v = h.new_value("n", "e")
        assert isinstance(v, functions.HistoryItem)


class TestListUtils:

    def test_remove_list_item(self):
        lst = [1, 2, 2, 3, 2]
        functions.remove_list_item(lst, 2)
        assert lst == [1, 3]

    def test_remove_list_item_none(self):
        functions.remove_list_item(None, 1)  # no error

    def test_listremove(self):
        lst = [1, 1, 2]
        functions.listremove(lst, 1)
        assert lst == [2]

    def test_listmerge(self):
        assert functions.listmerge([1], [2]) == [1, 2]
        assert functions.listmerge([1, 2, 3], [2, 3, 4]) == [1, 2, 3, 4]

    def test_list_replace(self):
        assert functions.list_replace([1, 2, 3], 2, 9) == [1, 9, 3]

    def test_uniq_list_add(self):
        lst = []
        functions.uniq_list_add(lst, "a")
        functions.uniq_list_add(lst, "a")
        functions.uniq_list_add(lst, "")
        assert lst == ["a"]

    def test_uniq_list_add_not_ignore_empty(self):
        lst = []
        functions.uniq_list_add(lst, "", ignore_empty=False)
        assert lst == [""]

    def test_first_or_none(self):
        assert functions.first_or_none([]) is None
        assert functions.first_or_none([1, 2, 3]) == 1


class TestNumberAndDictUtils:

    def test_second_to_ms(self):
        assert functions.second_to_ms(1) == 1000
        assert functions.second_to_ms(2.5) == 2500

    def test_dictsort_value(self):
        d = {"a": 3, "b": 1, "c": 2}
        result = functions.dictsort(d, "value")
        assert [k for k, v in result] == ["b", "c", "a"]

    def test_dictsort_key(self):
        d = {"c": 3, "a": 1, "b": 2}
        result = functions.dictsort(d, "key")
        assert [k for k, v in result] == ["a", "b", "c"]

    def test_dictsort_unsupported(self):
        try:
            functions.dictsort({"a": 1}, "other")
            assert False
        except Exception as e:
            assert "unsupported" in str(e)

    def test_dictvalues(self):
        assert sorted(functions.dictvalues({"a": 1, "b": 2})) == [1, 2]

    def test_get_dict_values(self):
        assert functions.get_dict_values({"a": 1}) == [1]

    def test_del_dict_key(self):
        d = {"a": 1, "b": 2}
        functions.del_dict_key(d, "a")
        assert "a" not in d
        functions.del_dict_key(d, "missing")  # no error

    def test_delete_none_values(self):
        d = {"a": 1, "b": None, "c": None}
        functions.delete_None_values(d)
        assert d == {"a": 1}

    def test_delete_none_values_non_dict(self):
        try:
            functions.delete_None_values([1, None])
            assert False
        except ValueError:
            pass


class TestTypedDict:

    def test_get_dict(self):
        td = functions.TypedDict({"nested": {"x": 1}})
        sub = td.get_dict("nested")
        assert isinstance(sub, functions.TypedDict)
        empty = td.get_dict("missing")
        assert isinstance(empty, functions.TypedDict)
        assert dict(empty.dict_) == {}

    def test_get_list(self):
        td = functions.TypedDict({"lst": [1, 2]})
        assert td.get_list("lst") == [1, 2]
        assert td.get_list("missing", [9]) == [9]

    def test_get_list_bad_type(self):
        td = functions.TypedDict({"lst": "notalist"})
        try:
            td.get_list("lst")
            assert False
        except AssertionError:
            pass

    def test_get_int_bool_str(self):
        td = functions.TypedDict({"i": 5, "b": True, "s": "hi"})
        assert td.get_int("i") == 5
        assert td.get_int("missing") == 0
        assert td.get_bool("b") is True
        assert td.get_bool("missing") is False
        assert td.get_str("s") == "hi"
        assert td.get_str("missing") == ""

    def test_get(self):
        td = functions.TypedDict({"k": "v"})
        assert td.get("k") == "v"
        assert td.get("missing", "default") == "default"

    def test_getitem_str_repr(self):
        td = functions.TypedDict({"k": 1})
        assert td["k"] == 1
        assert "k" in str(td)
        assert "k" in repr(td)

    def test_dict_get_dict(self):
        assert functions.dict_get_dict({"a": {"b": 1}}, "a") == {"b": 1}
        assert functions.dict_get_dict({}, "a") == {}


class TestMiscFunctions:

    def test_safe_list(self):
        assert functions.safe_list([1, 2]) == [1, 2]
        assert functions.safe_list(set([1, 2])) == [1, 2]
        assert functions.safe_list("str") == []
        assert functions.safe_list(123) == []

    def test_iter_exists(self):
        assert functions.iter_exists(lambda x: x == 1, [1, 2, 3]) is True
        assert functions.iter_exists(lambda x: x == 1, [2, 3]) is False

    def test_pipe(self):
        def gt5(ctx):
            return [x for x in ctx if x > 5]

        def lt10(ctx):
            return [x for x in ctx if x < 10]

        assert functions.pipe([1, 6, 7, 10, 12], gt5, lt10) == [6, 7]

    def test_is_empty(self):
        assert functions.is_empty(None) is True
        assert functions.is_empty([]) is True
        assert functions.is_empty([1]) is False
        assert functions.is_empty("") is True


class TestTimer:

    def test_start_stop_cost(self):
        t = functions.Timer("test")
        t.start()
        t.stop()
        cost = t.cost()
        assert cost.endswith("ms")
        assert t.cost_millis() >= 0

    def test_context_manager(self):
        with functions.Timer("ctx") as t:
            assert t.name == "ctx"
        # after exit cost available
        assert t.cost_millis() >= 0


# ---------------------------------------------------------------------------
# xutils.tokenizer
# ---------------------------------------------------------------------------


def setup_ctx(text=""):
    """Build a fresh TokenizeContext so internal do_* functions can run."""
    ctx = tokenizer.TokenizeContext()
    ctx.line = 1
    ctx.col = 1
    ctx.text = text
    ctx.length = len(text)
    return ctx


class TestTokenAndHelpers:

    def test_token_init_default(self):
        tok = tokenizer.Token()
        assert tok.type == "symbol"
        assert tok.val is None

    def test_token_before_after(self):
        empty = tokenizer.Token(None, None, -1, -1)
        assert tokenizer._empty_token is not None
        assert empty.before() is tokenizer._empty_token
        assert empty.after() is tokenizer._empty_token

    def test_token_before_after_nonempty(self):
        tok = tokenizer.Token("symbol", "x", 1, 1)
        assert tok.before() is None
        assert tok.after() is None

    def test_token_str(self):
        tok = tokenizer.Token("symbol", "x", 1, 1)
        assert "val" in str(tok)

    def test_findpos_with_pos(self):
        tok = tokenizer.Token("symbol", "x", 2, 3)
        assert tokenizer.findpos(tok) == [2, 3]

    def test_findpos_without_pos(self):
        class NoPos:
            pass
        assert tokenizer.findpos(NoPos()) == [0, 0]

    def test_findpos_with_first(self):
        child = tokenizer.Token("symbol", "x", 5, 5)
        parent = type("P", (), {"first": child})()
        assert tokenizer.findpos(parent) == [5, 5]

    def test_find_error_line(self):
        s = "line1\nline2\nline3"
        r = tokenizer.find_error_line(s, [2, 1])
        assert "2: line2" in r
        assert "^" in r

    def test_report_error_with_token(self):
        tok = tokenizer.Token("symbol", "x", 1, 1)
        try:
            tokenizer.report_error("ctx", "src", tok, "msg")
            assert False
        except Exception as e:
            assert "Error at ctx" in str(e)

    def test_report_error_without_token(self):
        try:
            tokenizer.report_error("ctx", "src", None, "boom")
            assert False
        except Exception as e:
            assert "boom" in str(e)

    def test_clean(self):
        assert tokenizer.clean("a\r\nb") == "a\nb"

    def test_is_name_begin(self):
        assert tokenizer.is_name_begin("a") is True
        assert tokenizer.is_name_begin("Z") is True
        assert tokenizer.is_name_begin("_") is True
        assert tokenizer.is_name_begin("$") is True
        assert tokenizer.is_name_begin("1") is False
        assert tokenizer.is_name_begin(".") is False

    def test_is_name(self):
        assert tokenizer.is_name("a") is True
        assert tokenizer.is_name("1") is True
        assert tokenizer.is_name("_") is True
        assert tokenizer.is_name(".") is False

    def test_constants(self):
        assert "def" in tokenizer.KEYWORDS
        assert "=" in tokenizer.SYMBOLS
        assert "-" in tokenizer._ISYMBOLS


class TestTokenizerInternals:

    def test_do_symbol(self):
        ctx = setup_ctx("==")
        i = tokenizer.do_symbol(ctx, 0)
        assert i == 2
        assert ctx.res[-1].type == "=="

    def test_do_symbol_single(self):
        ctx = setup_ctx("+")
        i = tokenizer.do_symbol(ctx, 0)
        assert i == 1
        assert ctx.res[-1].val == "+"

    def test_do_symbol_invalid_raises(self):
        ctx = setup_ctx("!")
        # '!' is in _ISYMBOLS but not in SYMBOLS, so do_symbol raises
        try:
            tokenizer.do_symbol(ctx, 0)
            assert False
        except Exception:
            pass

    def test_do_number(self):
        ctx = setup_ctx("123")
        i = tokenizer.do_number(ctx, 0)
        assert i == 3
        assert ctx.res[-1].val == 123.0

    def test_do_number_decimal(self):
        ctx = setup_ctx("1.5")
        i = tokenizer.do_number(ctx, 0)
        assert i == 3
        assert ctx.res[-1].val == 1.5

    def test_do_name_keyword(self):
        ctx = setup_ctx("def")
        i = tokenizer.do_name(ctx, 0)
        assert i == 3
        assert ctx.res[-1].type == "def"

    def test_do_name_identifier(self):
        ctx = setup_ctx("my_var1")
        i = tokenizer.do_name(ctx, 0)
        assert i == 7
        assert ctx.res[-1].type == "name"
        assert ctx.res[-1].val == "my_var1"

    def test_do_string_double(self):
        ctx = setup_ctx('"hello"')
        i = tokenizer.do_string(ctx, 0)
        assert i == 7
        assert ctx.res[-1].val == "hello"

    def test_do_string_single(self):
        ctx = setup_ctx("'world'")
        i = tokenizer.do_string(ctx, 0)
        assert i == 7
        assert ctx.res[-1].val == "world"

    def test_do_string_escapes(self):
        ctx = setup_ctx('"a\\nb"')
        i = tokenizer.do_string(ctx, 0)
        assert i == len(ctx.text)
        assert ctx.res[-1].val == "a\nb"

    def test_do_string_other_escapes(self):
        ctx = setup_ctx('"a\\rb\\0c\\bd"')
        i = tokenizer.do_string(ctx, 0)
        assert i == len(ctx.text)
        val = ctx.res[-1].val
        assert val == "a" + chr(13) + "b" + "\0" + "c" + "\b" + "d"

    def test_do_string_triple(self):
        ctx = setup_ctx('"""docstring"""')
        i = tokenizer.do_string(ctx, 0)
        assert i == len(ctx.text)
        assert ctx.res[-1].val == "docstring"

    def test_do_comment(self):
        ctx = setup_ctx("# simple")
        i = tokenizer.do_comment(ctx, 0)
        assert i == len(ctx.text)
        # no token added for plain comment
        assert len(ctx.res) == 0

    def test_do_comment_debugger(self):
        ctx = setup_ctx("#@debugger foo")
        i = tokenizer.do_comment(ctx, 0)
        assert i == len(ctx.text)
        assert ctx.res[-1].val == "debugger"

    def test_do_nl(self):
        ctx = setup_ctx("a\nb")
        i = tokenizer.do_nl(ctx, 1)
        assert i == 2
        assert ctx.res[-1].type == "nl"

    def test_do_indent(self):
        ctx = setup_ctx("    x")
        i = tokenizer.do_indent(ctx, 0)
        # 4 spaces consumed
        assert i == 4
        assert "indent" in [t.type for t in ctx.res]

    def test_indent_dedent(self):
        ctx = setup_ctx()
        tokenizer.indent(ctx, 4)
        assert "indent" in [t.type for t in ctx.res]
        tokenizer.indent(ctx, 0)
        assert "dedent" in [t.type for t in ctx.res]


class TestTokenize:

    def test_tokenize_assignment(self):
        tokens = tokenizer.tokenize("a = 10")
        types = [t.type for t in tokens]
        assert "name" in types
        assert "=" in types
        assert "number" in types

    def test_tokenize_keywords(self):
        tokens = tokenizer.tokenize("def foo():\n    return 1")
        types = [t.type for t in tokens]
        assert "def" in types
        assert "return" in types
        assert "(" in types
        assert ")" in types
        assert ":" in types

    def test_tokenize_comment(self):
        tokens = tokenizer.tokenize("# this is a comment\nx = 1")
        # comment itself yields no token but line still processed
        vals = [t.val for t in tokens]
        assert "this is a comment" not in vals
        assert "x" in [t.val for t in tokens]

    def test_tokenize_string_with_cjk(self):
        # Chinese characters inside a string are valid tokens content
        tokens = tokenizer.tokenize('"中文测试"')
        assert tokens[-1].val == "中文测试"

    def test_tokenize_comment_with_cjk(self):
        tokens = tokenizer.tokenize("# 这是注释")
        # comment produces no token but should not raise
        assert isinstance(tokens, list)

    def test_tokenize_cjk_standalone_raises(self):
        # Standalone CJK chars are not valid identifier starts -> unknown token
        try:
            tokenizer.tokenize("中文 = 1")
            assert False, "expected unknown token error"
        except Exception:
            pass

    def test_tokenize_string_escape_cjk(self):
        tokens = tokenizer.tokenize('"a\\nb中文"')
        assert "b中文" in tokens[-1].val

    def test_tokenize_number_decimal(self):
        tokens = tokenizer.tokenize("x = 3.14")
        number_tokens = [t for t in tokens if t.type == "number"]
        assert number_tokens[0].val == 3.14

    def test_tokenize_notin_and_isnot(self):
        tokens = tokenizer.tokenize("if a is not b and c not in d:\n    pass")
        types = [t.type for t in tokens]
        assert "notin" in types
        assert "isnot" in types

    def test_tokenize_in_without_not(self):
        # 'in' not preceded by 'not' hits the else branch of TokenizeContext.add
        tokens = tokenizer.tokenize("x in y")
        types = [t.type for t in tokens]
        assert "in" in types
        assert "notin" not in types

    def test_tokenize_line_continuation(self):
        # backslash-newline continuation
        tokens = tokenizer.tokenize("a = 1 \\\n    + 2")
        # still parses as a single logical expression without nl between
        types = [t.type for t in tokens]
        assert "number" in types

    def test_loadfile(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as fp:
            fp.write("a = 1")
            fname = fp.name
        try:
            content = tokenizer.loadfile(fname)
            assert content == "a = 1"
            tokens = tokenizer.tokenize(content)
            assert "number" in [t.type for t in tokens]
        finally:
            os.remove(fname)
