# -*- coding: utf-8 -*-
"""SQLite 内存统计工具测试

验证随机采样、线程安全统计表、按页估算退化与 get_stats / get_total_memory_usage。
"""

import os
import tempfile
import sqlite3
import unittest

from xutils import _sqlite_mem


class TestSqliteMem(unittest.TestCase):

    def setUp(self):
        _sqlite_mem.reset_stats()

    def tearDown(self):
        _sqlite_mem.reset_stats()
        # 还原开关，避免影响其它用例
        _sqlite_mem.set_enabled(True)

    def _make_conn(self, with_data=False):
        # 使用临时文件，确保 PRAGMA database_list 能拿到真实路径
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        if with_data:
            conn.execute("CREATE TABLE t(x)")
            conn.executemany("INSERT INTO t VALUES(?)",
                             [(i,) for i in range(500)])
            conn.commit()
        self._path = path
        return conn

    def tearDownConn(self, conn):
        conn.close()
        try:
            os.remove(self._path)
        except OSError:
            pass

    def test_query_memory_returns_int(self):
        conn = self._make_conn(with_data=True)
        try:
            mem = _sqlite_mem._query_memory(conn)
            self.assertIsInstance(mem, int)
            self.assertGreaterEqual(mem, 0)
            if not _sqlite_mem.MEMORY_USED_AVAILABLE:
                # 退化为 page_count * page_size，有数据时应大于 0
                self.assertGreater(mem, 0)
        finally:
            self.tearDownConn(conn)

    def test_get_main_db_file(self):
        conn = self._make_conn()
        try:
            db_file = _sqlite_mem._get_main_db_file(conn)
            self.assertEqual(db_file, self._path)
        finally:
            self.tearDownConn(conn)

    def test_sample_records_stat(self):
        conn = self._make_conn(with_data=True)
        try:
            mem = _sqlite_mem.sample_current_connection(conn, probability=1.0)
            self.assertIsInstance(mem, int)
            self.assertGreaterEqual(mem, 0)
            # 统计表里应按数据库文件聚合出一条记录
            items = _sqlite_mem.get_stats()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].db_file, self._path)
            self.assertEqual(_sqlite_mem.get_total_memory_usage(), items[0].memory)
        finally:
            self.tearDownConn(conn)

    def test_sample_skip_when_probability_zero(self):
        conn = self._make_conn()
        try:
            mem = _sqlite_mem.sample_current_connection(conn, probability=0.0)
            self.assertEqual(mem, 0)
            # 未命中，不应写入统计表
            self.assertEqual(len(_sqlite_mem.get_stats()), 0)
        finally:
            self.tearDownConn(conn)

    def test_reset_stats(self):
        conn = self._make_conn(with_data=True)
        try:
            _sqlite_mem.sample_current_connection(conn, probability=1.0)
            self.assertGreater(len(_sqlite_mem.get_stats()), 0)
            _sqlite_mem.reset_stats()
            self.assertEqual(len(_sqlite_mem.get_stats()), 0)
        finally:
            self.tearDownConn(conn)

    def test_enabled_flag_toggle(self):
        _sqlite_mem.set_enabled(False)
        self.assertFalse(_sqlite_mem.is_enabled())
        _sqlite_mem.set_enabled(True)
        self.assertTrue(_sqlite_mem.is_enabled())
        # 字符串形式也应正确解析
        _sqlite_mem.set_enabled("0")
        self.assertFalse(_sqlite_mem.is_enabled())
        _sqlite_mem.set_enabled("1")
        self.assertTrue(_sqlite_mem.is_enabled())

    def test_disabled_skips_sampling(self):
        conn = self._make_conn(with_data=True)
        try:
            _sqlite_mem.set_enabled(False)
            mem = _sqlite_mem.sample_current_connection(conn, probability=1.0)
            # 关闭时直接返回 0，且不写入任何统计记录
            self.assertEqual(mem, 0)
            self.assertEqual(len(_sqlite_mem.get_stats()), 0)
            # 重新开启后应能正常采样
            _sqlite_mem.set_enabled(True)
            mem = _sqlite_mem.sample_current_connection(conn, probability=1.0)
            self.assertIsInstance(mem, int)
            self.assertEqual(len(_sqlite_mem.get_stats()), 1)
        finally:
            _sqlite_mem.set_enabled(True)
            self.tearDownConn(conn)


if __name__ == "__main__":
    unittest.main()
