
from xnote.core import xtables
from xutils import BaseDataRecord
from xutils import dateutil


class NoteRelationDO(BaseDataRecord):

    def __init__(self, **kw):
        now = dateutil.format_datetime()

        self.relation_id = 0
        self.ctime = now
        self.mtime = now
        self.user_id = 0
        self.relation_name = ""
        self.relation_note_id = 0
        self.note_id = 0
        self.target_id = 0

    def to_save_dict(self):
        result = dict(**self)
        result.pop("relation_id", None)
        return result


class _NoteRelationDaoImpl:

    db = xtables.get_table_by_name("note_relation")

    def list(self, note_id=0, target_id=0, user_id=0, offset=0, limit=20):
        where_sql = "user_id=$user_id"
        if note_id != 0:
            where_sql += " AND note_id=$note_id"
        if target_id != 0:
            where_sql += " AND target_id=$target_id"
        vars = dict(note_id=note_id, user_id=user_id, target_id=target_id)
        result = self.db.select(where=where_sql, vars=vars, offset=offset, limit=limit)
        return NoteRelationDO.from_dict_list(result)
    
    def get_by_id(self, relation_id=0, user_id=0):
        result = self.db.select_first(where=dict(relation_id=relation_id, user_id=user_id))
        return NoteRelationDO.from_dict_or_None(result)
    
    def insert(self, relation: NoteRelationDO):
        data = relation.to_save_dict()
        return self.db.insert(**data)
    
    def update(self, relation: NoteRelationDO):
        data = relation.to_save_dict()
        return self.db.update(where=dict(relation_id=relation.relation_id), **data)

    def save(self, relation: NoteRelationDO):
        if relation.relation_id > 0:
            return self.update(relation)
        else:
            return self.insert(relation)
        
    def delete(self, relation: NoteRelationDO):
        return self.db.delete(where=dict(relation_id=relation.relation_id))


NoteRelationDao = _NoteRelationDaoImpl()
