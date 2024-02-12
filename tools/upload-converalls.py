# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-02-07 11:05:46
@LastEditors  : xupingmao
@LastEditTime : 2024-02-07 11:11:17
@FilePath     : /xnote/tools/upload-converalls.py
@Description  : 描述
"""

# encoding=utf-8
import os
import time

def main():
    job_id = int(time.time())
    os.environ["MY_JOB_ID"] = str(job_id)
    os.environ["MY_BRANCH"] = "master"
    os.system(f"coveralls")

if __name__ == "__main__":
    main()
