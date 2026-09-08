# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-15 16:25:49
@LastEditors  : xupingmao
@LastEditTime : 2023-07-01 10:53:40
@FilePath     : /xnote/xutils/db/dbutil_cache.py
@Description  : 基于 kv_cache 表的持久化缓存

缓存的底层存储为 `kv_cache` SQL 表(定义在 `xnote/core/xtables.py` 的
`init_kv_cache_table`), 表结构如下:
    - cache_key   缓存的 key (varchar(100), 唯一索引)
    - cache_value 缓存的值 (text, JSON 序列化)
    - expire_time 失效时间戳, 0 表示不失效 (bigint)
    - user_id     用户ID, 可选字段 (bigint)

设计说明:
1. 读写都只需要 1 次 SQL 操作, 失效数据的清理也只需要按 expire_time 索引扫描
2. cache_key 列长度为 varchar(100), 当业务 key 长度超过哈希摘要的长度时,
   自动转换为哈希之后存储(默认 sha256), 避免超长 key 无法写入
"""
import time
import random
import hashlib
import logging
import typing

from xutils import interfaces
from xutils import jsonutil
from xutils.base import BaseDataRecord


class CacheRecord(BaseDataRecord):
    """kv_cache 表的记录"""

    id: int
    cache_key: str
    cache_value: str
    expire_time: int
    user_id: int

    def __init__(self):
        self.id = 0
        self.cache_key = ""
        self.cache_value = ""
        self.expire_time = 0
        self.user_id = 0


class KvCacheDao:
    """kv_cache 表的 DAO, 底层基于 SQL 表实现, 支持 TTL 过期"""

    table_name = "kv_cache"
    # cache_key 列的长度(varchar(100)), 与 xtables.init_kv_cache_table 保持一致
    CACHE_KEY_LEN = 100

    def __init__(self):
        # 延迟导入, 避免循环依赖, 同时确保 xtables.init() 已经执行
        from xnote.core import xtables
        self.table = xtables.get_table_by_name(self.table_name)

    def get_by_key(self, cache_key: str) -> typing.Optional[CacheRecord]:
        row = self.table.select_first(where=dict(cache_key=cache_key))
        return CacheRecord.from_dict_or_None(row)

    def put(self, cache_key: str, cache_value: str, expire_time: int = 0, user_id: int = 0) -> typing.Any:
        record = self.get_by_key(cache_key)
        if record is None:
            return self.table.insert(cache_key=cache_key,
                                     cache_value=cache_value,
                                     expire_time=expire_time,
                                     user_id=user_id)
        return self.table.update(where=dict(cache_key=cache_key),
                                 cache_value=cache_value,
                                 expire_time=expire_time,
                                 user_id=user_id)

    def delete_by_key(self, cache_key: str) -> typing.Any:
        return self.table.delete(where=dict(cache_key=cache_key))

    def count(self) -> int:
        return self.table.count()

    def delete_expired(self, now: float, limit: int = 1000) -> int:
        records = self.table.select(what="cache_key",
                                    where="expire_time > 0 AND expire_time < $now",
                                    vars=dict(now=now),
                                    limit=limit)
        count = 0
        for record in records:
            self.delete_by_key(record.cache_key)
            count += 1
        return count

    def list_keys_after(self, last_key: str, limit: int) -> typing.List[str]:
        if last_key == "":
            rows = self.table.select(what="cache_key",
                                     limit=limit,
                                     order="cache_key")
        else:
            rows = self.table.select(what="cache_key",
                                     where="cache_key > $last_key",
                                     vars=dict(last_key=last_key),
                                     limit=limit,
                                     order="cache_key")
        return [row.cache_key for row in rows]

    def list_keys(self, offset: int = 0, limit: int = 20) -> typing.List[str]:
        rows = self.table.select(what="cache_key",
                                 limit=limit,
                                 offset=offset,
                                 order="cache_key")
        return [row.cache_key for row in rows]


class DatabaseCache(interfaces.CacheInterface):
    """基于 kv_cache 表的持久化缓存, 支持 TTL 过期

    @param {str} hash_method 哈希算法, 默认 sha256。必须是 hashlib 支持的算法, 并且
                             其十六进制摘要长度不能超过 cache_key 列宽(100),
                             常用 md5/sha1/sha256/sha384。
                             max_key_len 由该算法推导, key 长度超过摘要长度时自动
                             转换为哈希存储, 即 sha256->64, sha1->40, md5->32
    """

    def __init__(self, hash_method: str = "sha256") -> None:
        self.hash_method = hash_method
        self.max_key_len = self._get_digest_len(hash_method)
        self.dao = KvCacheDao()
        self.last_scan_key = ""

    def _get_digest_len(self, hash_method: str) -> int:
        """校验哈希算法是否支持, 并返回其十六进制摘要的长度"""
        try:
            digest_len = len(hashlib.new(hash_method).hexdigest())
        except (ValueError, TypeError):
            raise ValueError("unsupported hash_method: %s" % hash_method)

        if digest_len > KvCacheDao.CACHE_KEY_LEN:
            raise ValueError("hash_method(%s) digest length(%s) exceeds cache_key column length(%s)" % (
                hash_method, digest_len, KvCacheDao.CACHE_KEY_LEN))

        return digest_len

    def _normalize_key(self, key: str) -> str:
        """key 长度超过阈值时, 转换为哈希之后存储"""
        if len(key) > self.max_key_len:
            return hashlib.new(self.hash_method, key.encode("utf-8")).hexdigest()
        return key

    def _get_row(self, key: str) -> typing.Optional[CacheRecord]:
        cache_key = self._normalize_key(key)
        return self.dao.get_by_key(cache_key)

    def get(self, key: str, default_value: typing.Any = None) -> typing.Any:
        row = self._get_row(key)
        if row is None:
            return default_value

        expire_time = row.expire_time
        if expire_time > 0 and expire_time < time.time():
            # 已失效
            self.delete(key)
            return default_value

        return jsonutil.from_json(row.cache_value)

    def put(self, key: str, value: typing.Any, expire: int = -1, expire_random: int = 600) -> typing.Any:
        assert expire > 0
        cache_key = self._normalize_key(key)
        expire_time = int(time.time() + expire)
        expire_time += random.randint(0, expire_random)
        cache_value = jsonutil.to_json(value)
        return self.dao.put(cache_key, cache_value, expire_time=expire_time)

    set = put

    def delete(self, key: str) -> typing.Any:
        cache_key = self._normalize_key(key)
        return self.dao.delete_by_key(cache_key)

    def clear_expired(self, limit: int = 1000) -> int:
        """清理失效的缓存, 返回本次扫描的 key 数量

        按 cache_key 有序分页扫描, 当数据量较大时分批记录扫描游标(last_scan_key),
        下次调用从游标位置继续, 避免单次扫描过多数据。
        """
        now = time.time()
        count = 0
        last_key = self.last_scan_key

        while count < limit:
            batch = self.dao.list_keys_after(last_key, limit)
            if len(batch) == 0:
                break
            for cache_key in batch:
                row = self.dao.get_by_key(cache_key)
                if row is not None:
                    expire_time = row.expire_time
                    if expire_time > 0 and expire_time < now:
                        self.dao.delete_by_key(cache_key)
                count += 1
                last_key = cache_key
            if len(batch) < limit:
                break

        if count < limit:
            # 扫描完成, 重置游标
            self.last_scan_key = ""
        else:
            self.last_scan_key = last_key

        logging.info("clear_expired count=%s, last_scan_key=%s", count, self.last_scan_key)
        return count

    def get_expire(self, key: str) -> int:
        row = self._get_row(key)
        if row is None:
            return 0
        return row.expire_time

    def list_keys(self, offset: int = 0, limit: int = 20) -> typing.List[str]:
        return self.dao.list_keys(offset=offset, limit=limit)

    def count(self) -> int:
        return self.dao.count()
