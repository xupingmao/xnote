# encoding=utf-8

from xnote.core import xtables
from xutils.base import BaseDataRecord
from xutils import dateutil

class TagCategoryDO(BaseDataRecord):

    def __init__(self, **kw):
        self.category_id = 0
        self.user_id = 0
        self.name = ""
        self.description = ""
        self.ctime = xtables.DEFAULT_DATETIME
        self.mtime = xtables.DEFAULT_DATETIME
        self.sort_order = 0
        self.tag_amount = 0
        self.update(kw)

    def to_save_dict(self):
        result = dict(**self)
        result.pop("category_id")
        return result

class TagCategoryDaoImpl:

    db = xtables.get_table_by_name("tag_category")

    def create(self, tag_category:TagCategoryDO):
        now = dateutil.format_datetime()
        tag_category.ctime = now
        tag_category.mtime = now
        save_dict = tag_category.to_save_dict()
        return self.db.insert(**save_dict)
    
    def save(self, category_info: TagCategoryDO):
        if category_info.category_id > 0:
            category_info.mtime = dateutil.format_datetime()
            save_dict = category_info.to_save_dict()
            return self.db.update(where=dict(category_id=category_info.category_id), **save_dict)
        else:
            return self.create(category_info)
    
    def list(self, user_id=0, limit=100):
        assert user_id > 0
        result_list = self.db.select(where=dict(user_id=user_id), limit=limit, order="sort_order")
        return TagCategoryDO.from_dict_list(result_list)
    
    def get_by_id(self, category_id=0):
        if category_id == 0:
            return None
        result = self.db.select_first(where=dict(category_id=category_id))
        return TagCategoryDO.from_dict_or_None(result)


TagCategoryDao = TagCategoryDaoImpl()
