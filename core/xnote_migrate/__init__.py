# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 22:57:09
# @modified 2021/12/31 22:57:10
# @filename __init__.py
import logging
import os
import xutils
from xutils import six

def migrate():
    logging.info("升级数据库中 ...")
    dirname = os.path.dirname(__file__)
    for fname in sorted(os.listdir(dirname)):
        if not fname.startswith("upgrade_"):
            continue
        if fname.startswith("upgrade_main"):
            continue
        basename, ext = os.path.splitext(fname)
        try:
            mod_name = "xnote_migrate." + basename
            mod = six._import_module(mod_name)
            logging.info("执行升级: %s", mod_name)
            mod.do_upgrade()
        except Exception as e:
            xutils.print_exc()
            logging.info("升级数据库失败!")
            raise e

    logging.info("数据库升级完成!")
