# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 22:57:09
# @modified 2021/12/31 22:57:10
# @filename __init__.py
import logging
import os
import importlib
import xutils
from xnote.core import xconfig

def migrate():
    logging.info("升级数据库中 ...")
    from xnote.service.system_meta_service import SystemMetaEnum
    dirname = os.path.dirname(__file__)
    for fname in sorted(os.listdir(dirname)):
        if not fname.startswith("upgrade_"):
            continue
        if fname.startswith("upgrade_main"):
            continue
        basename, ext = os.path.splitext(fname)
        try:
            mod_name = "xnote_migrate." + basename
            mod = importlib.import_module(mod_name)
            logging.info("执行升级: %s", mod_name)
            mod.do_upgrade()
        except Exception as e:
            xutils.print_exc()
            logging.info("升级数据库失败!")
            raise e

    old_version = SystemMetaEnum.db_schema_version.meta_value_float
    new_version = xconfig.DatabaseConfig.db_schema_version
    if new_version > old_version:
        SystemMetaEnum.db_schema_version.save_meta(str(new_version))
        logging.info("update db_schema_version, old=%s, new=%s", old_version, new_version)

    logging.info("数据库升级完成!")
