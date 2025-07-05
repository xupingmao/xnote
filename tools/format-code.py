# -*- coding:utf-8 -*-
# @author mark
# @since 2022/04/23 16:20:25
# @modified 2022/04/23 16:29:02
# @filename format-code.py
import os
import sys

def format_code(fpath):
    os.system(f"{sys.executable} -m yapf -i {fpath}")


def main():
    format_code("xutils/dbutil.py")
    format_code("xutils/dbutil_base.py")
    format_code("xutils/fsutil.py")
    format_code("handlers/note/dao.py")



if __name__ == '__main__':
    main()