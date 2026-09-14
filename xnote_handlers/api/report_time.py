# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03/25
# 

"""报时"""

import os
import time
import xutils
from xnote.core import xconfig
from xutils import webutil

class handler:

    def GET(self):
        if xconfig.is_mute():
            return webutil.FailedResult(code="fail", message="mute")
        try:
            tm = time.localtime()
            if tm.tm_hour >= 0 and tm.tm_hour <= 6:
                return False
            if tm.tm_hour == 7 and tm.tm_min < 30:
                return False
            if tm.tm_min == 0:
                msg = "现在时间是%s点整" % tm.tm_hour
            else:
                msg = "现在时间是%s点%s分" % (tm.tm_hour, tm.tm_min)
            if tm.tm_hour >= 23:
                return False
                msg += "，夜深了，请注意休息"
            xutils.say(msg)
            # voice.Release()
            return webutil.SuccessResult()
        except Exception as e:
            return webutil.FailedResult(code="fail", message=str(e))

xurls = (
    r"/api/v1/report_time", handler,
)
