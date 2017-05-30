# encoding=utf-8
from handlers.base import *
import sqlite3
import os
import xutils
import xauth
import xconfig
from collections import OrderedDict

config = xconfig

def db_execute(path, sql, args = None):
    """需要保持字段的顺序"""
    db = sqlite3.connect(path)
    cursorobj = db.cursor()
    kv_result = []
    try:
        if args is None:
            cursorobj.execute(sql)
        else:
            cursorobj.execute(sql, args)
        result = cursorobj.fetchall()
        db.commit()
        for single in result:
            # 保持字段顺序
            resultMap = OrderedDict()
            for i, desc in enumerate(cursorobj.description):
                name = desc[0]
                resultMap[name] = single[i]
            kv_result.append(resultMap)

    except Exception as e:
        raise e
    finally:
        db.close()
    return kv_result

class handler(BaseHandler):

    @xauth.login_required("admin")
    def execute(self):
        sql = self.get_argument("sql", "")
        path = self.get_argument("path", "")
        result_list = []
        error = ""
        if sql != "" and path != "":
            # TODO execute sql
            try:
                realpath = os.path.join(config.DATA_PATH, path)
                result_list = db_execute(realpath, sql)
            except Exception as e:
                error = e
        path_list = []
        for p in os.listdir(config.DATA_PATH):
            if p.endswith(".db"):
                path_list.append(p)
        if len(result_list) > 0:
            keys = result_list[0].keys()
        else:
            keys = []
        self.render("tools/sql.html", 
            keys = keys, result_list = result_list, 
            sql = sql, error = error,
            path_list = path_list,
            path = path)

