# encoding=utf-8


import xutils
from xnote.core import xtables
from xutils import dateutil

class CommentTypeEnum:
    """枚举无法扩展,所以这里不用,从外部添加枚举值可以直接设置新的属性"""
    empty = ""
    note = "note"
    list_item = "list_item"

class Comment(xutils.Storage):
    def __init__(self):
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.type = ""
        self.user_id = 0
        self.target_id = 0

class CommentService:

    db = xtables.get_table_by_name("comment_index")

    def __init__(self):
        pass
    
    def create(self, user_id=0, target_id=0, type=""):
        now = dateutil.format_datetime()
        return self.db.insert(ctime=now, mtime=now, type=type, user_id=user_id, target_id=target_id)
    
    def build_where(self, user_id=0, target_id=0, date=None, type=""):
        date_like = date
        where = "1=1"
        if user_id != 0:
            where += " AND user_id = $user_id"
        if target_id != 0:
            where += " AND target_id = $target_id"
        if date != None and date != "":
            where += " AND ctime LIKE $date_like"
            date_like = date + "%"
        if type != "":
            where += " AND type=$type"
        
        vars = dict(type=type, user_id=user_id, target_id=target_id, date_like=date_like)
        return where, vars
    
    def list(self, user_id=0, target_id=0, date=None, type="", offset=0,limit=20, order="ctime desc", what="*"):
        if user_id ==0 and target_id == 0:
            raise Exception("user_id,target_id不能同时为0")
        
        where, vars = self.build_where(user_id=user_id, target_id=target_id,date=date,type=type)
        return self.db.select(where=where, vars=vars, offset=offset,limit=limit,order=order)

    def count(self, user_id=0, target_id=0, date=None,type=""):
        where, vars = self.build_where(user_id=user_id, target_id=target_id,date=date,type=type)
        return self.db.count(where=where, vars=vars)
    
    def delete_by_id(self, id=0):
        return self.db.delete(where=dict(id=id))