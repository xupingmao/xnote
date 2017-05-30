# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/04/01
# 

"""切换菜单样式"""

import web

class handler:
    """docstring for handler"""
    
    def GET(self):
        nav_position = web.cookies(nav_position = "top").nav_position
        if nav_position == "top":
            nav_position = "left"
        else:
            nav_position = "top"
        # 设置cookie
        web.setcookie("nav_position", nav_position, expires=24*3600*365)
        raise web.seeother("/system/sys")