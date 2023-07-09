# encoding=utf-8
from . import base
import xtables

def do_upgrade():
    base.execute_upgrade("013.20230616_user", migrate_user_20230616)


def migrate_user_20230616():
    new_table = xtables.get_user_table()
    def check_user_exists(record):
        id = record.get("id")
        found = new_table.select_first(where=dict(id=id))
        if found != None:
            return True
        name = record.get("name")
        found = new_table.select_first(where=dict(name=name))
        return found != None
        
    base.migrate_sqlite_table(new_table, "user", check_exist_func=check_user_exists)

