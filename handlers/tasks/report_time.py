# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03/25
# 

"""报时"""

from handlers.base import *
import time

class handler(BaseHandler):

    def execute(self):
        try:
            import comtypes.client as cc
            # dynamic=True不生成静态的Python代码
            voice = cc.CreateObject("SAPI.SpVoice", dynamic=True)
            tm = time.localtime()
            if tm.tm_hour >= 0 and tm.tm_hour <= 6:
                return False
            if tm.tm_hour == 7 and tm.tm_min < 30:
                return False
            msg = "现在时间是%s时%s分" % (tm.tm_hour, tm.tm_min)
            if tm.tm_hour >= 23:
                msg += "夜深了，请注意休息"
            voice.Speak(msg)
            voice.Release()
        except Exception as e:
            raise
        else:
            pass
        finally:
            return "OK"