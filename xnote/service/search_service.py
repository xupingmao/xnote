# encoding=utf-8
# @since 2024/10/26

import xutils
import typing
from xnote.core import xtables
from xutils import dateutil
from xutils.db.dbutil_helper import new_from_dict, new_from_dict_list


class SearchHistoryType:
    default = "default"
    note = "note"
    msg = "msg"

class SearchHistoryDO(xutils.Storage):

    def __init__(self):
        self.id = 0
        self.user_id = 0
        self.ctime = dateutil.format_datetime()
        self.cost_time_ms = 0
        self.search_type = ""
        self.search_key = ""

    @staticmethod
    def from_dict(dict_value):
        return new_from_dict(SearchHistoryDO, dict_value)
    
    @staticmethod
    def from_dict_list(dict_list) -> typing.List["SearchHistoryDO"]:
        return new_from_dict_list(SearchHistoryDO, dict_list)


class SearchHistoryService:

    db = xtables.get_table("search_history")

    @classmethod
    def create(cls, search_history: SearchHistoryDO):
        if len(search_history.search_key) >= 50:
            return
        if search_history.id == 0:
            search_history.pop("id", None)
        return int(cls.db.insert(**search_history))

    @classmethod
    def find_one(cls, user_id=0, ctime=None, search_type="", search_key=""):
        vars = dict(user_id=user_id, ctime=ctime, search_key=search_key, search_type=search_type)
        where_sql = "user_id = $user_id"
        if ctime != None:
            where_sql += " AND ctime=$ctime"
        if search_type != "":
            where_sql += " AND search_type=$search_type"
        if search_key != "":
            where_sql += " AND search_key=$search_key"

        first = cls.db.select_first(where=where_sql, vars=vars)
        if first is None:
            return None
        return SearchHistoryDO.from_dict(first)
    
    @classmethod
    def list(cls, user_id=0, search_type="", offset=0, limit=1000, order="ctime desc"):
        where_sql = "user_id=$user_id"
        if search_type != "":
            where_sql += " AND search_type=$search_type"
        vars = dict(user_id=user_id, search_type=search_type)
        records = cls.db.select(where=where_sql, vars=vars, offset=offset, limit=limit, order=order)
        return SearchHistoryDO.from_dict_list(records)

    @classmethod
    def count(cls, user_id=0, search_type=""):
        return cls.db.count(where=dict(user_id=user_id, search_type=search_type))

    @classmethod
    def delete_by_ids(cls, ids=[]):
        if len(ids) == 0:
            return 0
        return cls.db.delete(where="id in $ids", vars=dict(ids=ids))
    
    @classmethod
    def delete_items(cls, items: typing.List[SearchHistoryDO]):
        if len(items) == 0:
            return 0
        ids = [x.id for x in items]
        return cls.delete_by_ids(ids=ids)
