from xutils import Storage
from xutils import dateutil
from xutils import EnumItem, BaseEnum

class DictTypeItem(EnumItem):
    def __init__(self, name="", value="", table_name="", has_user_id=True):
        super().__init__(name, value)
        self.table_name = table_name
        self.has_user_id = has_user_id

class DictTypeEnum(BaseEnum):
    
    public = DictTypeItem("公共词典", "public", table_name = "dictionary", has_user_id=False)
    personal = DictTypeItem("个人词典", "personal", table_name = "dict_personal")
    relevant = DictTypeItem("关联词典", "relevant", table_name = "dict_relevant", has_user_id=False)


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
        self.dict_type = ""
    
    @classmethod
    def from_dict(cls, dict_value, dict_type=""):
        result = DictDO()
        result.update(dict_value)
        result.dict_type = dict_type
        if result.id > 0 and result.dict_id == 0:
            result.dict_id = result.id
        return result
    
    @classmethod
    def from_dict_list(cls, dict_list, dict_type=""):
        return [cls.from_dict(item, dict_type=dict_type) for item in dict_list]
    
    def get_save_dict(self):
        result = dict(**self)
        result.pop("id", None)
        result.pop("dict_id", None)
        result.pop("dict_type", None)
        return result
    
    @property
    def url(self):
        return f"/dict/update?dict_type={self.dict_type}&dict_id={self.dict_id}"
