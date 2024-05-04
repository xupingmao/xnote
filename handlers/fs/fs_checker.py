# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-05-04 23:00:54
@LastEditors  : xupingmao
@LastEditTime : 2024-05-04 23:15:15
@FilePath     : /xnote/handlers/fs/fs_checker.py
@Description  : 描述
"""

from xnote.core import xconfig
from xutils.base import XnoteException

def check_file_name(filename=""):
    if filename == "":
        raise XnoteException(code="400", message="文件名称为空")
    
    if ".." in filename:
        raise XnoteException(code="400", message="无效的文件名")
    
    max_file_name = xconfig.FileConfig.fs_max_name_length
    if len(filename) > max_file_name:
        raise XnoteException(code="400", message=f"文件名不能超过{max_file_name}")
