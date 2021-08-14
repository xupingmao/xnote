# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/05/18 09:44:13
# @modified 2021/08/14 10:21:56

import xutils
import xmanager
import xauth
from xtemplate import BasePlugin

class EventHandler(BasePlugin):
    
    title = '系统事件'
    category = "system"
    editable = False
    show_category = False
    
    def handle(self, content):
        self.rows = 0
        self.show_aside = False
        handlers = xmanager._event_manager._handlers
        
        for event_type in sorted(handlers.keys()):
            self.writeline('%s:' % event_type)
            hlist = handlers.get(event_type, [])
            for h in hlist:
                self.writeline('  %s' % h)
            self.writeline('')
    
xurls = (
    r"/system/event", EventHandler
)