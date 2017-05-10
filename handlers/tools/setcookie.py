# encoding=utf-8
import time
import json
import web
import xtemplate


"""设置服务器Cookie，用于本地测试

"""

html = """
<!DOCTYPE HTML>
<html>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <head>
        <title>Set-Cookie</title>
        <link rel="stylesheet" href="/static/css/xnote.css"/>
        <script src="/static/lib/jquery/jquery-2.2.3.min.js"></script>
    </head>

    <body>
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
    </body>

</html>
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
        # expires设置失效时间，不设置只在本次连接中生效
        # Path设置生效路径，不加端口号会隔离
        web.header("Set-Cookie", cookie + "; expires="+get_gmt_time() + "; Path=/")
        # dd = json.loads(cookie)
        # for key in dd:
            # web.header("Set-Cookie", cookie)
            # web.setcookie(key, dd.get(key), expires= 24 * 3600)
        return self.GET(cookie = cookie)



