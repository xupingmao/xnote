# -*- coding:utf-8 -*-
# Created on 2017/06/18
# Author: xupingmao 578749341@qq.com  
# Copyright (c) 2017
# 
# Last Modified

"""Description here"""
import time
import socket
import xutils

def check_network_health():
    try:
        infolist = socket.getaddrinfo('baidu.com', 80)
        return len(infolist) > 0
    except:
        return False

class handler:
    def GET(self):
        for i in range(1, 31):
            if not check_network_health():
                xutils.say("网络连接异常,重试第%s次" % i)
            else:
                xutils.say("网络连接正常")
                return dict(code="success")
            time.sleep(1)
        return dict(code="fail", message="网络连接异常")

