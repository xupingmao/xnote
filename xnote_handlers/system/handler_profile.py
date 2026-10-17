# -*- coding:utf-8 -*-
# 性能分析（profile），基于 BasePluginV2 + webui 组件开发
# created by xupingmao on 2017/06/30
import io
import profile
import threading
import web
import xutils
from xnote.plugin import BasePluginV2, ActionButton
from xnote.webui import Card, Textarea, ActionBar
from xnote_handlers.config import LinkConfig
from xutils import webutil

def get_stats(prof, sort=-1):
    import pstats
    buf = io.StringIO()
    stats = pstats.Stats(prof)
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


class ProfileHandler(BasePluginV2):

    title = "性能分析"
    require_admin = True
    parent_link = LinkConfig.develop_index

    def profile(self, url):
        headers = web.ctx.env
        data = web.data()

        def request_url(url, headers, data):
            quoted_url = xutils.quote_unicode(url)
            self.stats = runctx(
                "xmanager.request(url, method='GET',env=headers, data=data)",
                globals(), locals())

        # 新开一个线程，不然会破坏原来的上下文
        timer = threading.Timer(0, request_url, args=(url, headers, data))
        timer.start()
        timer.join()
        return self.stats

    def handle_default(self, action=""):
        # 分析表单（GET 提交，样式对齐原实现：textarea + 开始分析按钮）
        form_card = Card()
        form_card.add(Textarea(value="", name="url",
                              placeholder="请输入PATH,比如/note/index",
                              rows="2", css_class="row"))
        form_card.add(ActionButton(
            text="开始分析",
            css_class="btn",
            url="?action=query",
            data_names="url",
        ))
        self.add_component(form_card)

        # 分析结果
        result_card = Card()
        bar = ActionBar()
        bar.add_title("结果")    
        result_card.add(bar)
        result_card.add(Textarea("", css_class="row", rows="20", name="output"))
        self.add_component(result_card)

    def handle_query(self):
        url = xutils.get_argument_str("url")
        result_text = f"url = {url}\n"
        result_text += "-" * 30
        if url != "":
            result_text += "\n"
            result_text += str(self.profile(url))

        result = webutil.CommandsResult()
        result.add_command("update_text", name="output", value=result_text)
        return result

xurls = (
    r"/system/handler_profile", ProfileHandler,
)
