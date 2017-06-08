# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/08
# 

"""闹钟"""

import time
import xutils

class handler:
    

    def GET(self, msg):
        msg = xutils.unquote(msg)
        for i in range(3):
            xutils.say(msg)
            time.sleep(5)
        return dict(code="success")

xurls = (r"/tasks/alert/(.*)", handler)
