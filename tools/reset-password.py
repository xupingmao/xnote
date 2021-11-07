# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/02 00:48:23
# @modified 2021/11/07 14:12:57
# @filename reset-password.py

"""重置admin用户密码"""

import sys
sys.path.append(".")

import app
app.init_app()

import xauth

print("===== Before =====")
print(xauth.get_user_by_name("admin"))

xauth.update_user("admin", dict(password = "123456"))

print("===== After =====")
print(xauth.get_user_by_name("admin"))
