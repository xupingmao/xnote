# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-14 14:53:37
@LastEditors  : xupingmao
@LastEditTime : 2022-05-14 16:58:31
@FilePath     : /xnote/xutils/db/shard.py
@Description  : 数据库分片
"""

import json
from xutils import netutil

# 多路读取分页实现


class ShardCursor:
    """分片游标，负责从固定的一个分片读写数据"""

    def __init__(self, url, params):
        self.url = url
        self._has_next = True
        self.data = []
        self.params = params
        self.offset = 0
        self.limit = 20
        self._debug = False

    def set_debug(self, debug):
        self._debug = debug

    def has_next(self):
        return self._has_next

    def first(self):
        assert len(self.data) > 0, "Must call after check cursor.has_next()"
        return self.data[0]

    def next(self):
        assert len(self.data) > 0
        self.data = self.data[1:]

    def check_and_read(self):
        if not self._has_next:
            return
        if len(self.data) > 0:
            return
        self.data = self._read_from_server()
        if len(self.data) == 0:
            self._has_next = False

    def _read_from_server(self):
        """从服务器读取数据
        TODO: 这个可以做成异步的，在wait_read_done里面等待异步完成，这样多个分片就可以并行查询"""
        params = dict(
            offset=self.offset,
            limit=self.limit,
            data=self.params,
        )

        raw_data = netutil.http_post(self.url, body=json.dumps(params))
        result = json.loads(raw_data)
        if result.get("code") == 0:
            data = result.get("data")
            if self._debug:
                print("url:", self.url, "data:", data)
            self.offset += len(data)
            return data
        print("read failed:", result)
        raise Exception("read failed, code:%s" % result.get("code"))

    def wait_read_done(self):
        pass


class ShardManager:
    """分片管理器，负责从多个分片读写数据"""

    def __init__(self):
        self.shards = []
        self._debug = False

    def add_shard(self, url):
        self.shards.append(url)

    def set_debug(self, debug):
        self._debug = debug

    def has_next(self, cursors):
        for cursor in cursors:
            if cursor.has_next():
                return True
        return False

    def check_and_read(self, cursors):
        for cursor in cursors:
            assert isinstance(cursor, ShardCursor)
            cursor.check_and_read()

        for cursor in cursors:
            assert isinstance(cursor, ShardCursor)
            cursor.wait_read_done()

    def read_min_value(self, cursors):
        min_value = None
        min_cursor = None

        for cursor in cursors:
            assert isinstance(cursor, ShardCursor)

            if not cursor.has_next():
                continue

            value = cursor.first()
            assert value != None

            if min_value == None:
                min_value = value
                min_cursor = cursor
            elif value["key"] < min_value["key"]:
                min_value = value
                min_cursor = cursor

        if min_cursor != None:
            min_cursor.next()

        return min_value

    def query_page(self, page_no, page_size, params):
        assert len(self.shards) > 0, "No available shards"
        assert isinstance(params, dict), "Params must be dict"

        cursors = []
        for shard in self.shards:
            cursor = ShardCursor(shard, params)
            if self._debug:
                cursor.set_debug(True)
            cursors.append(cursor)

        page = 1
        while page <= page_no:
            data = []
            while len(data) < page_size:
                self.check_and_read(cursors)

                if not self.has_next(cursors):
                    return data

                min_value = self.read_min_value(cursors)
                assert min_value != None
                data.append(min_value)

            if page == page_no:
                return data
            page += 1
