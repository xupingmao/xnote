# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/08
# 

"""闹钟"""

import time
import xutils
import xconfig

class handler:
    def GET(self, msg=None):
        repeat  = xutils.get_argument("repeat", 3, type=int)
        content = xutils.get_argument("content")
        repeat = min(10, repeat)
        if msg is None:
            msg = content
        if xconfig.is_mute():
            return dict(code="fail", message="mute")
        msg = xutils.unquote(msg)
        for i in range(repeat):
            xutils.say(msg)
            time.sleep(2)
        return dict(code="success")

xurls = (
    r"/api/alarm/(.*)", handler,
    r"/api/alert/(.*)", handler,
    r"/api/alarm", handler,
)
