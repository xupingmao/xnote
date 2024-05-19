# encoding=utf-8

from . import test_base
import sys
import os
import time
import random
import unittest
import xutils
from xnote.core import xconfig
import doctest
import datetime
from xutils import textutil
from xutils import cacheutil
from xutils import fsutil
from xutils import dbutil
from xutils import Storage, dateutil

def get_tmp_fpath():
    count = 0
    while count < 100:
        fpath = os.path.join("./testdata/test_%04d.tmp" % count)
        if os.path.exists(fpath):
            count += 1
        else:
            return fpath
    raise Exception("get_tmp_fpath failed, too many retries")

class TestMain(unittest.TestCase):
    def test_quote_unicode(self):
        result = xutils.quote_unicode("http://测试")
        self.assertEqual("http://%E6%B5%8B%E8%AF%95", result)
        result = xutils.quote_unicode("http://test/测试")
        self.assertEqual("http://test/%E6%B5%8B%E8%AF%95", result)
        r1 = xutils.quote_unicode("测试")
        r2 = xutils.quote_unicode(r1)
        self.assertEqual(r1, r2) # 重复encode是安全的

    def test_quote_unicode_2(self):
        result = xutils.quote_unicode("http://test?name=测试")
        self.assertEqual("http://test?name=%E6%B5%8B%E8%AF%95", result)
        result = xutils.quote_unicode("http://test?name=测试&age=10")
        self.assertEqual("http://test?name=%E6%B5%8B%E8%AF%95&age=10", result)

    def test_get_opt(self):
        # 不好用
        import getopt
        opts, args = getopt.getopt(["--data","/data", "--log", "/log/log.log"], "x", ["data=", "log="])
        print()
        print(opts)
        print(args)
        self.assertEqual(opts[0], ("--data", "/data"))

    def test_argparse(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("-a", action="store", default=False)
        parser.add_argument("--data", default="./data")
        parser.add_argument("--test", default=True)
        result = parser.parse_args(["-a", "1", "--data", "/data"])
        print()
        print(result)
        self.assertEqual(True, hasattr(result, "data"))
        self.assertEqual(False, hasattr(result, "not_exists"))
        self.assertEqual("1", result.a)
        self.assertEqual("/data", result.data)
        self.assertEqual(True, result.test)

    def test_get_relative_path(self):
        path   = "./test/test.html"
        parent = "./"
        relative_path = xutils.get_relative_path(path, parent)
        self.assertEqual("test/test.html", relative_path)

        path   = "./test.html"
        parent = "./"
        relative_path = xutils.get_relative_path(path, parent)
        self.assertEqual("test.html", relative_path)

        path = "./test/test.html"
        parent = "./test"
        relative_path = xutils.get_relative_path(path, parent)
        self.assertEqual("test.html", relative_path)

    def test_splitpath(self):
        if not xutils.is_windows():
            path = "/root/test"
            pathlist = xutils.splitpath(path)
            self.assertEqual(2, len(pathlist))

    def test_decode_name(self):
        self.assertEqual("a.txt", xutils.decode_name("a.txt"))
        self.assertEqual("a.txt", xutils.decode_name("YS50eHQ=.x0"))
        self.assertEqual("a.txt", xutils.decode_name("YS50eHQ.x0"))
        self.assertEqual("a.txt", xutils.decode_name("YS50eHQ=.xenc"))

    def test_encode_name(self):
        self.assertEqual("YS50eHQ.x0", xutils.encode_name("a.txt"))
        self.assertEqual("YS50eHQ.x0", xutils.encode_name("YS50eHQ.x0"))

    def test_edit_distance(self):
        self.assertEqual(1, xutils.edit_distance("abcd","abc"))
        self.assertEqual(2, xutils.edit_distance("abcd", "ab"))
        self.assertEqual(6, xutils.edit_distance("abc", "def"))
        self.assertEqual(3, xutils.edit_distance("kkabcd", "abc"))

    def test_jaccard_similarity(self):
        from xutils.textutil import jaccard_similarity, jaccard_distance
        str1 = 'hello'
        str2 = 'hell0'
        self.assertEqual(3.0/5, jaccard_similarity(str1, str2))
        self.assertEqual(1-3.0/5, jaccard_distance(str1, str2))

    def test_bs4(self):
        html = "<p>hello<p><p>world</p>"
        if xutils.bs4 is not None:
            soup = xutils.bs4.BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator=" ")
            self.assertEqual("hello world", text)


    def test_search_path(self):
        print(os.getcwd())
        result = xutils.search_path("./", "*test*")
        self.assertTrue(len(result) > 0)

    def test_storage(self):
        obj = xutils.Storage(name="name")
        self.assertEqual(obj.name, "name")
        self.assertEqual(obj.value, None)

    def test_storage_default(self):
        # 删除了默认值的特性，会影响遍历功能，如果需要自行继承实现一套
        obj = xutils.Storage(name="name")
        self.assertEqual(obj.value, None)

    def test_save_file(self):
        tmpfile = os.path.join(xconfig.DATA_DIR, "tmp.txt")
        xutils.savetofile(tmpfile, "test")
        content = xutils.readfile(tmpfile)
        self.assertEqual("test", content)
        xutils.remove(tmpfile, True)

    def test_match_time(self):
        tm = time.strptime("2015-01-01", "%Y-%m-%d")
        self.assertFalse(xutils.match_time(year = 2016, tm = tm))
        self.assertTrue(xutils.match_time(month = 1, tm = tm))


    def test_history(self):
        h = xutils.History("test", 3)
        h.add(1)
        h.add(2)
        h.add(3)
        h.add(4)
        self.assertEqual(len(h), 3)

    def test_exec_code(self):
        code = "print(123)"
        xutils.exec_python_code(name='test', code = code, record_stdout = False, raise_err = True)

    def test_mark_text(self):
        text = "hello world"
        html = xutils.mark_text(text)
        self.assertEqual("hello&nbsp;world", html)

        text = "a link https://link"
        html = xutils.mark_text(text)
        self.assertEqual('a&nbsp;link&nbsp;<a target="_blank" href="https://link">https://link</a>', html)

        # text = 'Link [name](/http)'
        # html = xutils.mark_text(text)
        # self.assertEqual('Link&nbsp;<a href="/http">name</a>', html)
        text = "file:///data/files/admin/upload/2024/05/5Lit5paHLmpwZw.x0"
        html = xutils.mark_text(text)
        expect_html = """<div class="msg-img-box"><img class="msg-img x-photo" alt="/data/files/admin/upload/2024/05/5Lit5paHLmpwZw.x0" src="/data/files/admin/upload/2024/05/5Lit5paHLmpwZw.x0"></div>"""
        self.assertEqual(expect_html, html)

    def test_marked_text_parser(self):
        from xutils.text_parser import runtest
        runtest()

    def test_count_alpha(self):
        text = "abc def 123"
        self.assertEqual(6, textutil.count_alpha(text))

    def test_count_digit(self):
        text = "abc def 123"
        self.assertEqual(3, textutil.count_digit(text))

    def test_textutil(self):
        import doctest
        doctest.testmod(m=xutils.textutil, verbose=True)

    def test_netutil(self):
        import doctest
        from xutils import netutil
        doctest.testmod(m=netutil, verbose=True)

    def test_dateutil(self):
        import doctest
        doctest.testmod(m=xutils.dateutil, verbose=True)

    def test_dateutil_get_days_of_month(self):
        year = random.randint(2000, 3000)
        for month in range(1,13):
            xutils.dateutil.get_days_of_month(year, month)
            
    def test_dateutil_date_add(self):
        st = dateutil.parse_date_to_struct("2023-10-01")
        y, m, d = dateutil.date_add(tm=st, months=3)
        assert (y,m,d) == (2024,1,1)
        
        y, m, d = dateutil.date_add(tm=st, months=-1)
        assert (y,m,d) == (2023,9,1)
        
        y, m, d = dateutil.date_add(tm=st, months=-10)
        assert (y,m,d) == (2022,12,1)

        y, m, d = dateutil.date_add(tm=st, days=2)
        assert (y,m,d) == (2023,10,3)
        
    def test_fsutil(self):
        import doctest
        doctest.testmod(m=xutils.fsutil, verbose=True)

    def test_fsutil_read(self):
        test_content = "Test"
        fpath   = get_tmp_fpath()
        fsutil.writefile(fpath, test_content)
        encoding = fsutil.detect_encoding(fpath)
        content  = fsutil.readfile(fpath)
        lines    = fsutil.readlines(fpath)

        self.assertEqual("utf-8", encoding)
        self.assertEqual("Test",  content)
        self.assertEqual(["Test"], lines)

    def test_htmlutil(self):
        import doctest
        doctest.testmod(m=xutils.htmlutil, verbose=True)

    def test_functions(self):
        from xutils import functions
        import doctest
        doctest.testmod(m=functions, verbose=True)

    def test_dbutil(self):
        from xutils import dbutil
        doctest.testmod(m=dbutil, verbose=True)

    def test_print_table(self):
        xutils.print_table([dict(name="a", age=10), dict(name="b", age=12)])

    def skip_test_http_get(self):
        out = xutils.http_get("http://baidu.com")

    def skip_test_http_download(self):
        fname = "baidu_tmp.html"
        xutils.http_download("http://baidu.com", fname)
        os.remove(fname)

    def test_splithost(self):
        host, path = xutils.splithost("http://example.com/hello")
        self.assertEqual("example.com", host)
        self.assertEqual("/hello", path)

    def test_short_text(self):
        # 足够
        v = textutil.short_text('abcd', 10)
        self.assertEqual('abcd', v)
        v = textutil.short_text(u'中文123', 4)
        self.assertEqual(u'中文123', v)

        # 刚好
        v = textutil.short_text('012345', 3)
        self.assertEqual('012345', v)
        v = textutil.short_text(u'中文1234', 4)
        self.assertEqual(u'中文1234', v)

        # 不够
        v = textutil.short_text(u'中文12345678', 4)
        self.assertEqual(u'中文12..', v)
        # 奇数个半角
        v = textutil.short_text(u'中文1中文中文', 4)
        self.assertEqual(u'中文1..', v)
        v = textutil.short_text(u'BUG及问题记录', 5)
        self.assertEqual(u'BUG及问..', v)

        v = textutil.short_text(u'1234中国人', 4)
        self.assertEqual(u'1234中..', v)

    def test_RecordList(self):
        rl = xutils.RecordList()
        rl.visit('test')
        rl.visit('name')
        records = rl.recent()
        self.assertEqual(2, len(records))
        self.assertEqual('name', records[0].name)

    def test_MemTable_list(self):
        table = xutils.MemTable(100)
        table.insert(name='t1', age=8)
        table.insert(name='t2', age=9)
        table.insert(name='t3', age=10)
        table.insert(name='t4', age=12)
        result = table.list(0, 1, lambda x:x.get('age')>=10)
        self.assertEqual(1, len(result))
        self.assertEqual('t3', result[0]['name'])

    def test_MemTable_first(self):
        table = xutils.MemTable(100)
        table.insert(name='t1', age=8)
        table.insert(name='t2', age=9)
        table.insert(name='t3', age=10)
        table.insert(name='t4', age=12)
        result = table.first(lambda x:x.get('age')>=10)
        assert result != None
        self.assertEqual('t3', result['name'])

    def test_tokenizer(self):
        from xutils import tokenizer
        content = '''
            this is a example
            a = 10
            c = 'a string'
            float = 1.2
            '''
        tokens = tokenizer.tokenize(content)

    def test_listmerge(self):
        from xutils import functions
        l1 = [1,2,3]
        l2 = [3,4,5]
        self.assertEqual([1,2,3,4,5], functions.listmerge(l1, l2))

    def test_dbutil_ldb_table(self):
        dbutil.register_table("unit_test", "单元测试")
        table = dbutil.LdbTable("unit_test")

        # 先清空测试数据
        rows = table.list()
        for row in rows:
            table.delete(row)

        # 插入测试
        row = Storage(name = "system-test", value = "value")
        new_id = table.insert(row, id_type = "timeseq")
        new_key = "unit_test:" + new_id
        # 查询测试
        new_row = table.get_by_key(new_key)
        self.assertTrue(new_row != None)

        # 更新测试
        table.update_by_key(new_key, Storage(value = "value333"))
        # 确认更新成功
        record = table.get_by_key(new_key)
        assert record != None
        self.assertEqual("value333", record["value"])

        # 删除测试
        table.delete_by_key(new_key)
        # 确认删除成功
        self.assertTrue(table.get_by_key(new_key) == None)

    def test_dbutil_ldb_table_user(self):
        dbutil.register_table("unit_test_user", "用户维度单元测试")
        table = dbutil.LdbTable("unit_test_user")
        user_name = "test_user"

        # 先清空测试数据
        rows = table.list()
        for row in rows:
            table.delete(row)

        # 插入数据测试
        row = Storage(name = "test", value = "value")
        table.insert_by_user(user_name, row)
        self.assertEqual(1, table.count())

        # 查询测试
        found_row = table.list_by_user(user_name)[0]
        self.assertTrue(found_row != None)
        self.assertTrue(table.get_by_key(found_row._key) != None)
        self.assertEqual(1, table.count_by_user(user_name))

        # 判断方法测试
        self.assertTrue(table.is_valid_key("unit_test_user:222"))
        self.assertTrue(table.is_valid_key("unit_test_user:test_user:222", user_name = "test_user"))

        # 更新测试
        found_row.value = "value222"
        table.update(found_row)
        record = table.get_by_key(found_row._key)
        assert record != None
        self.assertEqual("value222", record["value"])

        # 删除测试
        table.delete(found_row)
        self.assertEqual(0, table.count())

    def test_dbutil_hash(self):
        dbutil.register_table("hash_test", "hash表测试")
        db = dbutil.get_hash_table("hash_test")
        for key, value in db.iter(limit = -1):
            db.delete(key)

        db.put("key1", "value1")
        db.put("key2", "value2")

        self.assertEqual("value1", db.get("key1"))
        self.assertEqual(2, db.count())

        for key, value in db.iter(limit = -1):
            db.delete(key)

        self.assertEqual(0, db.count())

    def test_b64encode(self):
        text_input = "测试1234"
        text_output = xutils.b64encode(text_input)
        self.assertEqual("5rWL6K-VMTIzNA", text_output)

    def test_b64decode(self):
        text_input = "5rWL6K-VMTIzNA"
        text_output = xutils.b64decode(text_input)
        self.assertEqual("测试1234", text_output)

    def test_count_end_nl(self):
        text_input = "abc\n\n"
        self.assertEqual(2, textutil.count_end_nl(text_input))

    
    def test_module_call(self):
        def module_method(name):
            print("my name is", name)
            return True

        xutils.register_func("test.method", module_method)

        mod = xutils.Module("test")

        # 运行两次触发缓存
        mod.invoke("method", "test")
        method_result = mod.invoke("method", "test")
        self.assertTrue(method_result)
        self.assertTrue(len(mod._meth) == 1)

    def test_has_tag(self):
        code = "# @disabled"
        meta = xutils.load_script_meta_by_code(code)
        self.assertTrue(meta.has_tag("disabled"))

    def test_md5(self):
        input_text = "hello"
        self.assertEqual("5d41402abc4b2a76b9719d911017c592", textutil.md5_hex(input_text))


    def test_mark_text_tag(self):
        text = "test**mark**end"
        from xutils.text_parser import TextParser
        parser = TextParser()
        tokens = parser.parse(text)
        self.assertEqual(tokens[0], "test")
        self.assertEqual(tokens[1], "<span class=\"msg-strong\">mark</span>")
        self.assertEqual(tokens[2], "end")

    def test_random_int64(self):
        """测试下随机数的冲突"""
        values = set()
        times = 1000

        from xutils import numutil
        for i in range(times):
            values.add(numutil.create_random_int64())
        assert len(values) == times


    def test_json(self):
        from xutils import jsonutil
        obj = Storage(name="test",age=10,clazz=Storage)
        json_str = jsonutil.tojson(obj)
        assert """{"name":"test","age":10,"clazz":"<class>"}""" == json_str
        parsed_obj = jsonutil.parse_json_to_dict(json_str)
        assert parsed_obj.get("name") == "test"
        assert parsed_obj.get("age") == 10
        assert parsed_obj.get("clazz") == "<class>"

        