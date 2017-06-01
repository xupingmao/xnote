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
            msg = "现在时间是%s时%s分" % (tm.tm_hour, tm.tm_min)
            voice.Speak(msg)
            voice.Release()
        except Exception as e:
            raise
        else:
            pass
        finally:
            return "OK"