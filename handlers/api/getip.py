# encoding=utf-8
# getip 
# Created on 2017/09/26
# @modified 2019/07/12 00:52:34
import web
import xutils
import xtemplate

def get_real_ip():
    real_ip_list = web.ctx.env.get("HTTP_X_FORWARDED_FOR")
    if real_ip_list != None and len(real_ip_list) > 0:
        return real_ip_list.split(",")[0]
    return web.ctx.env.get("REMOTE_ADDR")

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
        yield "\n"

class JsonpHandler:

    tpl = """
{{callback}}({
    real_ip: "{{real_ip}}"
});
    """

    def GET(self):
        callback = xutils.get_argument_str("callback", "callback")
        real_ip = get_real_ip()
        return xtemplate.render_text(self.tpl, real_ip = real_ip, callback = callback)

xurls = (
    r"/api/getip", handler,
    r"/api/getip.jsonp", JsonpHandler,
)