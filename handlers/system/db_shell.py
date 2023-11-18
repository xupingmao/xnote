# encoding=utf-8
# @since 2017/02/19
# @modified 2022/03/18 23:34:21
import sqlite3
import os
import xutils
import time
import logging
from xnote.core import xauth, xconfig, xtemplate, xtables

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
    
    def do_execute(self):
        path = xutils.get_argument_str("path")
        sql = xutils.get_argument_str("sql")
        action = xutils.get_argument_str("action")
        result_list = []
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
        if len(result_list) > 0:
            keys = result_list[0].keys()
        else:
            keys = []
        return keys, result_list, error

    def handle_mysql(self,sql=""):
        if sql == "":
            return [], [], ""
        db = xtables.get_default_db_instance()
        try:
            result = db.query(sql)
        except:
            error = xutils.print_exc()
            return [],[],error
        result_list = []

        for record in result:
            if len(result_list) > 100:
                logging.info("too many results")
                break
            result_list.append(record)

        return result.names, result_list, ""


    @xauth.login_required("admin")
    def POST(self):
        sql = xutils.get_argument_str("sql")
        path = xutils.get_argument_str("path")
        action = xutils.get_argument_str("action")
        type = xutils.get_argument_str("type")

        t_start = time.time()
        if type == "mysql":
            keys, result_list, error = self.handle_mysql(sql)
        else:
            keys, result_list, error = self.do_execute()
        t_stop = time.time()


        kw = xutils.Storage()
        kw.cols = keys
        kw.show_right = False
        kw.result_list = result_list
        kw.sql = sql
        kw.error = error
        kw.cost_time = int((t_stop-t_start)*1000)
        kw.path = path

        return xtemplate.render("system/page/sqlite.html", **kw)

    def GET(self):
        return self.POST()


xurls = (
    r"/system/sqlite", handler,
)