# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03/25
# 

"""故意抛出一个异常"""

class handler(object):
    
    def GET(self):
        raise Exception("For Development Test")
