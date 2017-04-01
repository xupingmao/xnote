# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/04/01
# 

"""切换菜单样式"""

import web
import config

class handler:
    """docstring for handler"""
    
    def GET(self):
        if config.nav_position == "top":
            config.nav_position = "left"
        else:
            config.nav_position = "top"
        raise web.seeother("/system/sys")