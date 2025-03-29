# encoding=utf-8
import web
import typing

from datetime import datetime
from xutils import dateutil
from handlers.note.dao import NoteIndexDao
from handlers.note.models import NoteDO, NoteIndexDO
from xnote.core import xconfig
from xnote.core import xauth
from handlers.note import dao_share
from xnote.plugin.table import DataTable, TableActionType
from handlers.note.dao_relation import NoteRelationDao

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
    
    def get_table(self, note_id=0, user_id=0):
        table = DataTable()

        table.add_head("关系ID", "relation_id")
        table.add_head("关系名称", "relation_name")
        table.add_head("关联笔记", "target_name", link_field="target_url")
        table.add_action(title="编辑", type=TableActionType.edit_form, link_field="edit_url")
        table.add_action(title="删除", type=TableActionType.confirm, link_field="delete_url", 
                         msg_field="delete_msg", css_class="btn danger")
        

        relation_list = NoteRelationDao.list(user_id=user_id, note_id=note_id)
        note_id_list = [item.target_id for item in relation_list]
        name_dict = NoteIndexDao.get_name_dict(note_id_list=note_id_list)

        for relation in relation_list:
            target_name = name_dict.get(relation.target_id, "")
            relation["target_url"] = f"/note/view/{relation.target_id}"
            relation["edit_url"] = f"/note/relation?action=edit&relation_id={relation.relation_id}&note_id={relation.note_id}"
            relation["delete_url"] = f"/note/relation?action=delete&relation_id={relation.relation_id}"
            relation["delete_msg"] = f"确定删除关系【{relation.relation_name}-{target_name}】吗"
            relation["target_name"] = target_name
            table.add_row(relation)

        return table

NoteRelationService = _NoteRelationServiceImpl()
