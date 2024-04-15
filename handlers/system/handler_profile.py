# encoding=utf-8
# created by xupingmao on 2017/06/30
# Last Modified 
import io
import profile
import threading
import web
import xutils
from xnote.core import xauth
from xnote.core import xtemplate

html = """
{% extends base %}

{% block body_left %}
{% init url = "" %}
{% init result = "" %}

<div class="col-md-12 card">
    {% set title = "性能分析" %}
    {% include common/base_title.html %}
</div>


<div class="card">
    <form method="GET">
    <textarea class="col-md-12" name="url" placeholder="请输入PATH,比如/note/index">{{url}}</textarea>
    <button>开始分析</button>
    </form>
</div>

<div class="card">
    <span>结果</span>
    <textarea class="row" rows=20>{{result}}</textarea>
</div>

{% end %}

{% block body_right %}
    {% include common/sidebar/default.html %}
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

class ProfileHandler:

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
        return xtemplate.render_text(html, template_name="handler_profile", url=url, result=result)

xurls = (
    r"/system/handler_profile", ProfileHandler,
)