# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-07 16:39:30
@LastEditors  : xupingmao
@LastEditTime : 2022-08-07 17:26:13
@FilePath     : /xnote/tools/android-main.py
@Description  : 安卓入口，可以运行在qpython的环境中
"""
import os

# 切换工作目录
project_dir = os.path.dirname(__file__)
os.chdir(project_dir)

from xnote.core import xnote_app
xnote_app.main(boot_config_kw = dict(db_driver = "sqlite"))


