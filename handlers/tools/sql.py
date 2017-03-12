from handlers.base import *
import FileDB
import sqlite3
import os
import xutils


class handler(BaseHandler):

    def execute(self):
        sql = self.get_argument("sql", "")
        path = self.get_argument("path", "")
        result_list = []
        error = ""
        if sql != "" and path != "":
            # TODO execute sql
            try:
                realpath = os.path.join("db", path)
                result_list = xutils.db_execute(realpath, sql)
            except Exception as e:
                error = e
        path_list = []
        for p in os.listdir("db"):
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

