# encoding=utf-8
# @since 2017/02/19
# @modified 2022/03/18 23:34:21
import sqlite3
import os
import xutils
import xauth
import xconfig
import xtemplate
import time
import logging

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
        db.commit()
        db.close()
    return kv_result

class handler:

    def get_result_by_action(self, action, path):
        if action == "show_tables":
            return db_execute(path, "SELECT * FROM sqlite_master;")
        if action == "count_tables":
            result = []
            table_names = db_execute(path, "SELECT name FROM sqlite_master WHERE type = ?;", ("table",))
            for name_row in table_names:
                name = name_row["name"]
                amount = db_execute(path, "SELECT COUNT(1) AS amount FROM %s" % name)[0].get("amount")
                row = OrderedDict()
                row["name"] = name
                row["amount"] = amount
                result.append(row)
            return result

        return []

    @xauth.login_required("admin")
    def POST(self):
        sql = xutils.get_argument("sql", "")
        path = xutils.get_argument("path", "")
        action = xutils.get_argument("action", "")
        result_list = []
        t_start = time.time()
        error = ""
        logging.info("path:(%s), sql:(%s)", path, sql)

        if sql == "" and path != "":
            result_list = self.get_result_by_action(action, path)
        
        if sql != "" and path != "":
            try:
                realpath = path
                result_list = db_execute(realpath, sql)
            except Exception as e:
                xutils.print_exc()
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
        return xtemplate.render("system/page/sqlite.html", 
            show_right = False,
            keys = keys, 
            result_list = result_list, 
            sql = sql, 
            error = error,
            cost_time = int((t_stop - t_start) * 1000),
            path_list = path_list,
            path = path)

    def GET(self):
        return self.POST()


xurls = (
    r"/system/sqlite", handler,
)