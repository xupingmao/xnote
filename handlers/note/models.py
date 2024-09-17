# encoding=utf-8
import enum
from xutils import Storage
from xutils import dateutil
from xnote.core import xtables
from xutils.db.dbutil_helper import new_from_dict


class NoteLevelEnum(enum.Enum):
    """笔记等级"""
    archived = -1 # 归档
    normal = 0 # 普通
    sticky = 1 # 置顶

class NoteIndexDO(Storage):
    def __init__(self, **kw):
        now = dateutil.format_datetime()
        self.id = 0
        self.name = ""
        self.creator = ""
        self.creator_id = 0
        self.type = ""
        self.ctime = now
        self.mtime = now
        self.atime = now
        self.dtime = xtables.DEFAULT_DATETIME
        self.parent_id = 0
        self.size = 0
        self.children_count = 0
        self.version = 0
        self.is_deleted = 0
        self.is_public = 0
        self.level = 0 # 等级 (-1)-归档 0-正常, 1-置顶
        self.tag_str = ""
        self.visit_cnt = 0
        self.update(kw)

    @staticmethod
    def from_dict(dict_value):
        return new_from_dict(NoteIndexDO, dict_value)
    
    def before_save(self, index_do):
        # type: (NoteDO) -> None
        tags = index_do.tags
        if tags == None:
            tags = []
        self.tag_str = " ".join(tags)

class NoteDO(Storage):
    def __init__(self):
        self.id = 0 # 笔记ID
        self.name = ""
        self.path = ""
        self.creator = ""
        self.creator_id = 0
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.atime = dateutil.format_datetime()
        self.dtime = xtables.DEFAULT_DATETIME # 删除时间
        self.type = "md"
        self.category = "" # 废弃
        self.size = 0
        self.children_count = 0
        self.parent_id = 0 # 默认挂在根目录下
        self.content = ""
        self.data = ""
        self.is_deleted = 0 # 0-正常， 1-删除
        self.is_public = 0  # 0-不公开, 1-公开
        self.token = ""
        self.priority = 0 # (-1):归档, 0-正常, 1-置顶
        self.level = 0 # 等级 (-1):归档, 0-正常, 1-置顶
        self.visit_cnt = 0
        self.visited_cnt = 0
        self.orderby = ""
        # 热门指数
        self.hot_index = 0
        # 版本
        self.version = 0
        self.tags = []

        # 假的属性
        self.url = ""
        self.icon = ""
        self.show_edit = True
        self.badge_info = ""
        self.create_date = ""
        self.update_date = ""

    @classmethod
    def from_dict(cls, dict_value):
        result = NoteDO()
        result.update(dict_value)
        return result
    
    def before_save(self):
        remove_virtual_fields(self)

def del_dict_key(dict, key):
    dict.pop(key, None)

def remove_virtual_fields(note):
    del_dict_key(note, "url")
    del_dict_key(note, "icon")
    del_dict_key(note, "show_edit")
    del_dict_key(note, "create_date")
    del_dict_key(note, "badge_info")
    del_dict_key(note, "create_date")
    del_dict_key(note, "update_date")
    del_dict_key(note, "tag_info_list")


class NoteTokenType:
    note = "note"

class NoteToken(Storage):
    def __init__(self):
        self.type = ""
        self.id = 0
    
    @classmethod
    def from_dict(cls, dict_value):
        if dict_value == None:
            return None
        result = NoteToken()
        result.update(dict_value)
        return result
    
class NoteTypeInfo:

    def __init__(self, url="", name="", tag_code="", css_class=""):
        self.url = url
        self.name = name
        self.tag_code = tag_code
        self.css_class = css_class

    @classmethod
    def get_type_list(cls):
        return [
            NoteTypeInfo(url="/note/all", name="全部", tag_code="all"),
            NoteTypeInfo(url="/note/all?type=group", name="笔记本", tag_code="group"),
            NoteTypeInfo(url="/note/all?type=md", name="文档", tag_code="md"),
            NoteTypeInfo(url="/note/all?type=gallery", name="相册", tag_code="gallery"),
            NoteTypeInfo(url="/note/all?type=list", name="清单", tag_code="list"),
            NoteTypeInfo(url="/note/all?type=table", name="表格", tag_code="table"),
            NoteTypeInfo(url="/note/removed", name="回收站", tag_code="removed", css_class="hide"),
        ]