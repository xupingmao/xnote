from xutils import Storage
from xutils import dateutil
from xutils import EnumItem, BaseEnum
from xnote.core.models import SearchResult
from xnote.core.xtemplate import T


class DictTypeItem(EnumItem):
    def __init__(self, name="", value="", table_name="", has_user_id=True):
        super().__init__(name, value)
        self.table_name = table_name
        self.has_user_id = has_user_id

class DictTypeEnum(BaseEnum):
    
    personal = DictTypeItem("个人词典", "2", table_name = "dictionary")
    public = DictTypeItem("公共词典", "1", table_name = "dictionary", has_user_id=False)
    relevant = DictTypeItem("关联词典", "3", table_name = "dictionary", has_user_id=False)

    @classmethod
    def get_default(cls):
        return cls.personal


class DictDO(Storage):

    def __init__(self, **kw):
        super().__init__(**kw)

        now = dateutil.format_datetime()
        self.id = 0
        self.dict_id = 0
        self.user_id = 0
        self.key = ""
        self.value = ""
        self.ctime = now
        self.mtime = now
        self.dict_type = 0
    
    @classmethod
    def from_dict(cls, dict_value):
        result = DictDO()
        result.update(dict_value)
        if result.id > 0 and result.dict_id == 0:
            result.dict_id = result.id
        return result
    
    @classmethod
    def from_dict_list(cls, dict_list):
        return [cls.from_dict(item) for item in dict_list]
    
    def get_save_dict(self):
        result = dict(**self)
        result.pop("id", None)
        result.pop("dict_id", None)
        return result
    
    @property
    def url(self):
        return f"/dict/update?dict_type={self.dict_type}&dict_id={self.dict_id}"

    def to_search_result(self):
        result = SearchResult()
        if self.dict_type == DictTypeEnum.personal.int_value:
            result.name = f"个人词典: {self.key}"
        else:
            result.name = T("search_definition") % self.key
        result.raw = self.value
        result.url = self.url
        result.icon = "icon-dict"
        result.category = "dict"
        return result