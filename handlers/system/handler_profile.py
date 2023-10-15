# encoding=utf-8
# created by xupingmao on 2017/06/30
# Last Modified 
import io
import profile
import threading
import web
import xtemplate
import xutils
import xmanager
import xauth

html = """
{% extends base.html %}

{% block body %}
{% init url = "" %}
{% init result = "" %}

<h3>性能分析</h3>
<form method="GET">
<textarea class="col-md-12" name="url">{{url}}</textarea>
<button>submit</button>
</form>

<pre>{{result}}</pre>

{% end %}
"""

def get_stats(self, sort=-1):
    import pstats
    buf = io.StringIO()
    stats = pstats.Stats(self);
    stats.stream = buf
    # 统计累计时间
    stats.strip_dirs().sort_stats('cumulative').print_stats()
    buf.seek(0)
    return buf.read()

def runctx(statement, globals, locals):
    prof = profile.Profile()
    try:
        prof.runctx(statement, globals, locals)
    except SystemExit:
        pass
    finally:
        return get_stats(prof)

class handler:
    def profile(self, url):
        headers = web.ctx.env
        data = web.data()
        def request_url(url, headers, data):
            quoted_url = xutils.quote_unicode(url)
            self.stats = runctx("xmanager.request(url, method='GET',env=headers, data=data)", globals(), locals())
        # 新开一个线程，不然会破坏原来的上下文
        timer = threading.Timer(0, request_url, args=(url, headers, data))
        timer.start()
        timer.join()
        return self.stats

    @xauth.login_required("admin")
    def GET(self):
        url = xutils.get_argument("url")
        result = ""
        if url is not None and url != "":
            result = self.profile(url)
        return xtemplate.render_text(html, url=url, result=result)

