# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-07 16:39:30
@LastEditors  : xupingmao
@LastEditTime : 2022-08-07 17:14:25
@FilePath     : /xnote/main.py
@Description  : 安卓入口
"""
import os

# 切换工作目录
project_dir = os.path.dirname(__file__)
os.chdir(project_dir)

import app
app.main(boot_config_kw = dict(db_driver = "sqlite"))


