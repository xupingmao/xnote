# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03/25
# 

"""报时"""

import os
import time
import xutils
import xconfig

class handler:

    def GET(self):
        if xconfig.is_mute():
            return dict(code="fail", message="mute")
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
            return dict(code="success", message="")
        except Exception as e:
            return dict(code="fail", message=str(e))
        else:
            pass
        finally:
            pass