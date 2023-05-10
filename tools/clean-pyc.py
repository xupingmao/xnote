# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-05-06 23:25:15
@LastEditors  : xupingmao
@LastEditTime : 2023-05-06 23:26:33
@FilePath     : /xnote/tools/clean-pyc.py
@Description  : 描述
"""

import os

def clean(dirname = "./"):
    for root, dirs, files in os.walk(dirname):
        for fname in files:
            if fname.endswith(".pyc"):
                fpath = os.path.join(root, fname)
                print("delete", fpath)
                os.remove(fpath)

if __name__ == "__main__":
    clean()