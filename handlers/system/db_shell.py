# encoding=utf-8
# @since 2017/02/19
# @modified 2022/03/18 23:34:21
import sqlite3
import os
import xutils
import time
import logging
import web.db

from urllib.parse import quote
from xnote.core import xauth, xconfig, xtemplate, xtables
from xnote.plugin import DataTable
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

    def get_result_by_action(self, action, path) -> DataTable:
        if action == "show_tables":
            args = ("index",)
            kv_result = db_execute(path, "SELECT type, name, tbl_name, rootpage FROM sqlite_master WHERE type != ?", args)            
            table = DataTable()
            table.add_head(title="type", field="type")
            table.add_head(title="tbl_name", field="tbl_name", link_field="name_link")
            table.add_head(title="rootpage", field="rootpage")
            for row in kv_result:
                name = row["tbl_name"]
                row["name_link"] = f"{xconfig.WebConfig.server_home}/system/db/struct?table_name={name}&dbpath={quote(path)}"
                table.add_row(row)
            return table
        
        if action == "count_tables":
            table = DataTable()
            table.add_head(title="name", field="name", link_field="name_link")
            table.add_head(title="amount", field="amount")

            table_names = db_execute(path, "SELECT name FROM sqlite_master WHERE type = ?;", ("table",))
            for name_row in table_names:
                name = name_row["name"]
                amount = db_execute(path, "SELECT COUNT(1) AS amount FROM %s" % name)[0].get("amount")
                row = OrderedDict()
                row["name"] = name
                row["amount"] = amount
                row["name_link"] = f"{xconfig.WebConfig.server_home}/system/db/struct?table_name={name}&dbpath={quote(path)}"
                table.add_row(row)
            return table

        return DataTable()
    
    def do_execute(self):
        path = xutils.get_argument_str("path")
        sql = xutils.get_argument_str("sql")
        action = xutils.get_argument_str("action")
        result_list = []
        error = ""
        logging.info("path:(%s), sql:(%s)", path, sql)

        if sql == "" and path != "":
            return self.get_result_by_action(action, path), ""
        
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
        return self.result_to_table(keys, result_list), error

    def handle_mysql(self,sql=""):
        if sql == "":
            return self.result_to_table([], []), ""
        db = xtables.get_default_db_instance()
        try:
            result = db.query(sql)
        except:
            error = xutils.print_exc()
            return self.result_to_table([], []),error
        
        assert isinstance(result, web.db.ResultSet)
        result_list = []

        for record in result:
            if len(result_list) > 100:
                logging.info("too many results")
                break
            result_list.append(record)

        return self.result_to_table(result.names, result_list), ""


    @xauth.login_required("admin")
    def POST(self):
        sql = xutils.get_argument_str("sql")
        path = xutils.get_argument_str("path")
        action = xutils.get_argument_str("action")
        type = xutils.get_argument_str("type")
        is_embed = xutils.get_argument_bool("embed")

        t_start = time.time()
        if type == "mysql":
            table, error = self.handle_mysql(sql)
        else:
            table, error = self.do_execute()
        t_stop = time.time()


        kw = xutils.Storage()
        kw.table = table
        kw.show_right = False
        kw.sql = sql
        kw.error = error
        kw.cost_time = int((t_stop-t_start)*1000)
        kw.path = path
        kw.is_embed = is_embed
        if is_embed:
            kw.show_nav = False

        return xtemplate.render("system/page/sqlite.html", **kw)

    def GET(self):
        return self.POST()
    
    def result_to_table(self, keys: list, result_list: list) -> DataTable:
        table = DataTable()
        for key in keys:
            table.add_head(title=key, field=key)
        
        table.set_rows(result_list)
        return table


xurls = (
    r"/system/sqlite", handler,
)