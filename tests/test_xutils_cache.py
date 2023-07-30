# -*- coding:utf-8 -*-
from .a import *
import time
import xutils
from xutils import cacheutil
# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

BaseTestCase = test_base.BaseTestCase

app = test_base.init()


@xutils.cache(prefix='fib')
def fib(n):
    if n == 1 or n == 2:
        return 1
    return fib(n-1) + fib(n-2)


class TestXutilCache(BaseTestCase):

    def test_cache_size(self):
        c = cacheutil.Cache(max_size=2)

        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)

        self.assertEqual(2, len(c.dict))
    
    def test_expire(self):
        c = cacheutil.Cache(max_size=2)

        c.put("a", 1, expire=1, random_range=0)
        value = c.get("a")
        self.assertEqual(1, value)
        time.sleep(2)
        value = c.get("a")
        self.assertIsNone(value)

    def test_prefixed_cache(self):
        c = cacheutil.PrefixedCache("p:")
        c.put("a", 10, expire=600)
        self.assertEqual(cacheutil._global_cache.get("p:a"), 10)


    def test_cache(self):
        self.assertEqual(9227465, fib(35))
        self.assertTrue(xutils.cache_del("fib(1,)"))

    def test_cache_set_delete(self):
        cacheutil.set("name", 123, expire = 600)
        self.assertEqual(123, cacheutil.get("name"))
        cacheutil.delete("name")
        self.assertEqual(None, cacheutil.get("name"))

    def test_cache_load_dump(self):
        cacheutil.load_dump()

    def test_cache_hash(self):
        cacheutil.hset("h01", "key", "value", expire = 600)
        value = cacheutil.hget("h01", "key")
        self.assertEqual("value", value)
        self.assertEqual(None, cacheutil.hget("h01", "key02"))

    def test_cache_call(self):
        counter = [0]
        def do_get_value():
            counter[0] += 1
            return counter[0]
        
        v1 = cacheutil.cache_call("cache_call", do_get_value, expire=600)
        v2 = cacheutil.cache_call("cache_call", do_get_value, expire=600)

        self.assertEqual(v1, 1)
        self.assertEqual(v2, 1)