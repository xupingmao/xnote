# encoding=utf-8
import time
import json
import web
import xtemplate


"""设置服务器Cookie，用于本地测试

"""

html = """{% extends base.html %}
{% block body %}
        {% init cookie = "" %}
        <form class="col-md-12" method="POST">
            <h2>Cookie</h2>
            <div id="cookie" class="col-md-12"></div>
            <textarea class="col-md-12" name="cookie" rows=20>{{cookie}}</textarea>
            <button>设置</button>
        </form>
        <script>
            $(function() {
                $("#cookie").html(document.cookie);
            });
        </script>   
{% end %}
"""

html2 = """
{% extends base.html %}

{% block body %}
    {% init cookie = "" %}
    <form class="col-md-12" method="POST">
        <h2>Cookie</h2>
        <textarea class="col-md-12" name="cookie" rows=20>{{cookie}}</textarea>
        <button>设置</button>
    </form>
{% end %}

"""

def get_gmt_time():
    seconds = time.time() + 24 * 3600
    st = time.localtime(seconds)
    return time.strftime('%a, %d %b %Y %H:%M:%S GMT', st)

class handler:

    def GET(self, **kw):
        return xtemplate.render_text(html, **kw)

    def POST(self):
        cookie = web.input().cookie
        cookie = cookie.rstrip()
        # Cookie格式 Set-Cookie: value[; expires=date][; domain=domain][; path=path][; secure]
        # expires设置失效时间，不设置只在本次连接中生效
        # Path设置生效路径，不加端口号会隔离
        # 多个cookie需要使用多个Set-Cookie首部
        # web.header("Set-Cookie", cookie + "; expires="+get_gmt_time() + "; Path=/")
        cookies = cookie.split(";")
        for ck in cookies:
            ck = ck.strip()
            parts = ck.split('=')
            if len(parts) == 2:
                key, value = parts
                web.setcookie(key, value, expires = 24 * 3600)

        # dd = json.loads(cookie)
        # for key in dd:
            # web.header("Set-Cookie", cookie)
            # web.setcookie(key, dd.get(key), expires= 24 * 3600)
        return self.GET(cookie = cookie)



