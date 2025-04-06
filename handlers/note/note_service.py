# encoding=utf-8
import web
import typing

from datetime import datetime
from xutils import dateutil
from handlers.note.dao import NoteIndexDao
from handlers.note.models import NoteDO, NoteIndexDO, NoteRelationGroup
from xnote.core import xconfig
from xnote.core import xauth
from handlers.note import dao_share
from xnote.plugin import TextLink
from xnote.plugin.table import DataTable, TableActionType
from handlers.note.dao_relation import NoteRelationDao, NoteRelationDO

class YearGroup:

    def __init__(self, year=0, amount=0):
        self.year = year
        self.amount = amount
        self.href = f"{xconfig.WebConfig.server_home}/note/timeline?type=year_group&year={year}"

    def to_dict(self):
        return dict(**self.__dict__)

class NoteService:
    @classmethod
    def get_year_group_list(cls, creator_id=0) -> typing.List[YearGroup]:
        min_year = NoteIndexDao.get_min_year(creator_id=creator_id)
        if min_year < 0:
            return []
        max_year = NoteIndexDao.get_max_year(creator_id=creator_id)
        if max_year < 0:
            return []
        
        result = []
        year = max_year
        while year >= min_year:
            date_start = dateutil.format_datetime(datetime(year=year, month=1, day=1))
            date_end_exclusive = dateutil.format_datetime(datetime(year=year+1, month=1, day=1))
            amount = NoteIndexDao.count(creator_id=creator_id, date_start=date_start, date_end_exclusive=date_end_exclusive)
            item = YearGroup(year=year, amount=amount)
            result.append(item)
            year-=1
        return result
        
    @classmethod
    def check_auth(cls, file: NoteIndexDO, user_id=0):
        if user_id == file.creator_id:
            return

        if file.is_public == 1:
            return

        if user_id == 0:
            xauth.redirect_to_login()

        # 笔记的分享
        if dao_share.get_share_to(user_id, file.id) != None:
            return

        # 笔记本的分享
        if dao_share.get_share_to(user_id, file.parent_id) != None:
            return

        raise web.seeother("/unauthorized")


class _NoteRelationServiceImpl:

    def get_note_url(self, note_id=0, tab="relation"):
        return f"/note/view/{note_id}?tab={tab}"

    def render_table(self, relation_list: typing.List[NoteRelationDO]):
        table = DataTable()
        table.add_head("关系ID", "relation_id")
        table.add_head("源笔记", "source_name", link_field="source_url")
        table.add_head("关系名称", "relation_name")
        table.add_head("关联笔记", "target_name", link_field="target_url")
        table.add_action(title="编辑", type=TableActionType.edit_form, link_field="edit_url")
        table.add_action(title="删除", type=TableActionType.confirm, link_field="delete_url", 
                         msg_field="delete_msg", css_class="btn danger")
        table.action_head.default_style.min_width = "120px"
        
        note_id_list = [] # type: list[int]
        for item in relation_list:
            note_id_list.append(item.note_id)
            note_id_list.append(item.target_id)
        name_dict = NoteIndexDao.get_name_dict(note_id_list=set(note_id_list))

        for relation in relation_list:
            source_name = name_dict.get(relation.note_id, "")
            target_name = name_dict.get(relation.target_id, "")
            relation["target_url"] = self.get_note_url(relation.target_id)
            relation["edit_url"] = f"/note/relation?action=edit&relation_id={relation.relation_id}&note_id={relation.note_id}"
            relation["delete_url"] = f"/note/relation?action=delete&relation_id={relation.relation_id}"
            relation["delete_msg"] = f"确定删除关系【{relation.relation_name}-{target_name}】吗"
            relation["target_name"] = target_name
            relation["source_name"] = source_name
            relation["source_url"] = self.get_note_url(relation.note_id)
            table.add_row(relation)

        return table

    
    def get_table(self, note_id=0, user_id=0):
        relation_list = NoteRelationDao.list(user_id=user_id, note_id=note_id)
        return self.render_table(relation_list)

    def get_rev_table(self, target_id=0, user_id=0, offset=0, limit=20):
        relation_list = NoteRelationDao.list(user_id=user_id, target_id=target_id)
        return self.render_table(relation_list)
    
    def get_related_notes(self, note_id=0, user_id=0, limit=10):
        list1 = NoteRelationDao.list(user_id=user_id, note_id=note_id, limit=limit)
        list2 = NoteRelationDao.list(user_id=user_id, target_id=note_id, limit=limit)
        related_notes = list1 + list2
        note_id_set = set()
        for item in related_notes:
            note_id_set.add(item.note_id)
            note_id_set.add(item.target_id)
        
        if note_id in note_id_set:
            note_id_set.remove(note_id)

        name_dict = NoteIndexDao.get_name_dict(note_id_list=note_id_set)
        result = [TextLink(text=name_dict.get(note_id, ""), href=self.get_note_url(note_id, tab="")) for note_id in note_id_set]
        result.sort(key = lambda x:x.text)
        return result

    def get_group_list(self, note_id=0, user_id=0):
        relation_list = NoteRelationDao.list(user_id=user_id, note_id=note_id, limit=100)
        note_id_list = [item.target_id for item in relation_list]
        name_dict = NoteIndexDao.get_name_dict(note_id_list=note_id_list)

        result_dict = {} # type: dict[str, NoteRelationGroup]

        for relation in relation_list:
            target_name = name_dict.get(relation.target_id, "")
            group = result_dict.get(relation.relation_name)
            if group is None:
                group = NoteRelationGroup()
                group.label = relation.relation_name
                
            group.label = relation.relation_name
            group.children.append(TextLink(href=f"/note/view/{relation.target_id}", text=target_name))
            result_dict[relation.relation_name] = group
        
        keys = sorted(result_dict.keys())
        result_list = [] # type: list[NoteRelationGroup]
        for key in keys:
            result_list.append(result_dict[key])
        return result_list

NoteRelationService = _NoteRelationServiceImpl()
