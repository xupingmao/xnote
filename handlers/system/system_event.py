# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/05/18 09:44:13
# @modified 2022/03/12 11:07:34

import xmanager
from xtemplate import BasePlugin
from xutils import Storage


HTML = r"""
<style>
    .card-body {
        display:none;
    }
</style>

<div class="row">
    <div class="card btn-line-height">
        <span>系统一共注册{{event_handler_count}}个事件处理器</span>
    </div>

    {% for index, event_type in enumerate(event_type_list) %}
        {% set temp_handler_list = handlers.get(event_type) %}
        <div class="card">
            <div class="card-title">
                <a id="{{event_type}}">{{event_type}}</a>
                <span>({{len(temp_handler_list)}})</span>
                <div class="float-right">
                    <button class="toggle-btn btn-default" data-index="{{index}}" data-toggle="折叠">展开</button>
                </div>
            </div>
            <div class="card-body event-body-{{index}}">
            {% for temp_handler in temp_handler_list %}
                <div class="list-item">{{temp_handler}}</div>
            {% end %}
            </div>
        </div>
    {% end %}

    <script>
    $(function () {
        $(".toggle-btn").click(function () {
            // 切换展示状态
            var index = $(this).attr("data-index");
            $(".event-body-" + index).toggle();

            // 切换文本
            var text = $(this).text();
            var toggle = $(this).attr("data-toggle");
            $(this).attr("data-toggle", text);
            $(this).text(toggle);
        }); 
    });
    </script>
</div>
"""

ASIDE_HTML = """
{% include system/component/admin_nav.html %}
"""

class EventHandler(BasePlugin):
    
    title = '系统事件'
    title_style = "left"
    category = "system"
    editable = False
    show_category = False
    show_title = True
    show_aside = True
    
    def handle(self, content):
        self.rows = 0
        self.show_aside = True
        event_type_list = []
        handlers = xmanager._event_manager._handlers
        event_type_list = sorted(handlers.keys())
        
        count = 0
        for key in event_type_list:
            count += len(handlers.get(key))
        
        kw = Storage()
        kw.handlers = handlers
        kw.event_type_list = event_type_list
        kw.event_handler_count = count
        self.writehtml(HTML, **kw)
        self.write_aside(ASIDE_HTML)
    
xurls = (
    r"/system/event", EventHandler
)