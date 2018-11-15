# encoding=utf-8
# @modified 2018/11/14 00:15:54
import sqlite3
import os
import xutils
import xauth
import xconfig
import xtemplate
import time
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

class handler:

    @xauth.login_required("admin")
    def POST(self):
        sql = xutils.get_argument("sql", "")
        path = xutils.get_argument("path", "")
        result_list = []
        t_start = time.time()
        error = ""
        if sql != "" and path != "":
            # TODO execute sql
            try:
                realpath = path
                result_list = db_execute(realpath, sql)
            except Exception as e:
                error = e
        t_stop = time.time()
        path_list = []
        for p in os.listdir(xconfig.DATA_DIR):
            if p.endswith(".db"):
                p = os.path.join(xconfig.DATA_DIR, p)
                path_list.append(p)
        if path == "" and len(path_list) > 0:
            path = path_list[0]
        if len(result_list) > 0:
            keys = result_list[0].keys()
        else:
            keys = []
        return xtemplate.render("tools/sql.html", 
            show_aside = False,
            keys = keys, 
            result_list = result_list, 
            sql = sql, 
            error = error,
            cost_time = int((t_stop - t_start) * 1000),
            path_list = path_list,
            path = path)

    def GET(self):
        return self.POST()

