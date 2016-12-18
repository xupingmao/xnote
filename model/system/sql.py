from BaseHandler import *
import FileDB

class handler(BaseHandler):

    def execute(self):
        sql = self.get_argument("sql", "")
        result_list = []
        error = ""
        if sql != "":
            # TODO execute sql
            if sql.lower().lstrip().startswith(("update", "alter", "insert")):
                error = "can not update/alter/insert database"
            else:
                try:
                    db = FileDB.FileDB()
                    result_list = db.execute(sql)
                except Exception as e:
                    error = e
        if len(result_list) > 0:
            keys = result_list[0].keys()
        else:
            keys = []
        self.render("system/sql.html", keys = keys, result_list = result_list, sql = sql, error = error)