# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/04/23
# 

"""Text To Speach"""

import xutils
from handlers.base import BaseHandler

class handler(BaseHandler):

    def default_request(self):
        content = self.get_argument("content")
        # print(content)
        import comtypes.client as cc
        # dynamic=True不生成静态的Python代码
        voice = cc.CreateObject("SAPI.SpVoice", dynamic=True)
        try:
            voice.Speak(content)
        finally:
            # 报异常
            # voice.Release()
            return "OK"