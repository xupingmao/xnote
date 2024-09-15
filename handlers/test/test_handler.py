# encoding=utf-8

import xutils
import web
import time


class handler:    
    def GET(self):
        return "success"


class TestCacheHandler:

    def format_time(self, gmtime):
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime)

    def GET(self):
        cache_type = xutils.get_argument_int("type")
        etag = xutils.get_argument_str("etag")
        if cache_type == 1:
            return self.get_cache_1()
        
        environ = web.ctx.environ
        client_etag = environ.get('HTTP_IF_NONE_MATCH')
        if_modified_since = environ.get("HTTP_IF_MODIFIED_SINCE")
        print(f"client_etag={client_etag}, if_modified_since={if_modified_since}")

        modified = time.gmtime()
        expires = time.gmtime(time.time() + 3600*24)

        web.header("Last-Modified", self.format_time(modified))
        web.header("Etag", etag)
        web.header("Expires", self.format_time(expires))
        return "test cache"
    
    def get_cache_1(self):
        expire_seconds = 3600 * 24
        web.header("Cache-Control", "public")
        web.header("Cache-Control", f"max-age={expire_seconds}")
        web.header("Vary", "User-Agent")
        return "test cache"


xurls = (
    r"/test", handler,
    r"/test/cache", TestCacheHandler,
)
