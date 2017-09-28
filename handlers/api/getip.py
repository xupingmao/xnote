# encoding=utf-8
# getip 
# Created on 2017/09/26
import web
import xtables
import xutils

class handler:

    def GET(self):
        # X-Forwarded-For是RFC 7239（Forwarded HTTP Extension）定义的扩展首部，大部分代理支持
        # 格式如下：
        # X-Forwarded-For: client, proxy1, proxy2
        # 而X-Real-IP目前不属于任何标准
        # See https://imququ.com/post/x-forwarded-for-header-in-http.html
        yield "X-Forwarded-For: "
        yield web.ctx.env.get("HTTP_X_FORWARDED_FOR")
        yield "\nRemote Addr: "
        yield web.ctx.env.get("REMOTE_ADDR")