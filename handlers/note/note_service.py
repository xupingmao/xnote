# encoding=utf-8
import web
from datetime import datetime
from xutils import dateutil
from handlers.note.dao import NoteIndexDao
from handlers.note.models import NoteDO
from xnote.core import xconfig
from xnote.core import xauth
from handlers.note import dao_share
import typing

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
    def check_auth(cls, file: NoteDO, user_id=0):
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
