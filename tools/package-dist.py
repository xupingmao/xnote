# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-07 15:58:30
@LastEditors  : xupingmao
@LastEditTime : 2022-08-07 17:15:46
@FilePath     : /xnote/tools/package-dist.py
@Description  : 打包成压缩文件
"""


import zipfile
import sys
import os
import fire

print("__file__=", __file__)
project_root = os.path.dirname(os.path.dirname(__file__))
lib_dir = os.path.join(project_root, "lib")
sys.path.append(project_root)
sys.path.append(lib_dir)

from xutils import fsutil


def zip_append(zip: zipfile.ZipFile, fpath, parent = "."):
    if os.path.isdir(fpath):
        # todo
        for child_name in os.listdir(fpath):
            child_path = os.path.join(fpath, child_name)
            zip_append(zip, child_path, parent = parent)
    else:
        relative_path = fsutil.get_relative_path(fpath, parent)
        zip.write(fpath, relative_path)

def main(target = "xnote.zip"):
    if os.path.exists(target):
        print("打包失败, 文件%s已经存在" % target, file = sys.stderr)
        sys.exit(1)
    
    # 创建文件
    with open(target, "w"):
        pass

    zip = zipfile.ZipFile(target, "w")
    zip_append(zip, "config")
    zip_append(zip, "xnote")
    zip_append(zip, "handlers")
    zip_append(zip, "lib")
    zip_append(zip, "static")
    zip_append(zip, "tools")
    zip_append(zip, "xutils")
    zip_append(zip, "app.py")
    zip_append(zip, "README.md")
    zip_append(zip, "COPYING")
    zip.write("tools/android-main.py", "main.py")
    zip.close()

if __name__ == "__main__":
    fire.Fire(main)
