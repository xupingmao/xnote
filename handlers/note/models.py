# encoding=utf-8
import enum
import typing

from xutils import Storage
from xutils import dateutil
from xnote.core import xtables
from xnote.core import xconfig
from xutils.db.dbutil_helper import new_from_dict


NOTE_ICON_DICT = {
    "group": "fa-folder",

    "post": "fa-file-word-o",  # 废弃
    "html": "fa-file-word-o",  # 废弃
    "gallery": "fa-photo",
    "list": "fa-list",
    "plan": "fa-calendar-check-o",

    # 表格类
    "csv": "fa-table",  # 废弃
    "table": "fa-table",  # 废弃
    "form": "fa-table",  # 开发中
}


class NoteLevelEnum(enum.Enum):
    """笔记等级"""
    archived = -1 # 归档
    normal = 0 # 普通
    sticky = 1 # 置顶

class NoteIndexDO(Storage):
    def __init__(self, **kw):
        super().__init__()
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
    
    @classmethod
    def from_dict_list(cls, dict_list):
        # type: (list[dict]) -> list[NoteIndexDO]
        result = []
        for item in dict_list:
            obj = cls()
            obj.update(item)
            obj.compat_old()
            result.append(obj)
        return result

    def before_save(self, index_do):
        # type: (NoteDO) -> None
        tags = index_do.tags
        if tags == None:
            tags = []
        self.tag_str = " ".join(tags)

    def compat_old(self):
        self.tags = self.get_tags()
        self.priority = self.level
        if self.__class__ != NoteDO:
            self.content = ""
            self.data = ""
        self.orderby = ""
        self.category = ""
        self.badge_info = ""
        self.show_next = False
        self.url = f"{xconfig.WebConfig.server_home}/note/view/{self.id}"
        self.icon = NOTE_ICON_DICT.get(self.type)

    def get_tags(self):
        return self.tag_str.split()

    @property
    def visited_cnt(self):
        return self.visit_cnt
    
    @property
    def archived(self):
        return self.level<0
    
    def set_archived(self, archived):
        if archived == True:
            self.level = -1
        if archived == False:
            self.level = 0

    @property
    def hot_index(self):
        return self.visit_cnt

class NoteDO(NoteIndexDO):
    def __init__(self):
        super(NoteDO, self).__init__()
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
        self.orderby = ""
        # 版本
        self.version = 0
        self.tags = []

        # 假的属性
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
    
    @classmethod
    def from_dict_or_None(cls, dict_value):
        if dict_value is None:
            return None
        return cls.from_dict(dict_value)
    
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
            NoteTypeInfo(url="/note/sticky?type=sticky", name="置顶", tag_code="sticky"),
            NoteTypeInfo(url="/note/group_list?type=group", name="笔记本", tag_code="group"),
            NoteTypeInfo(url="/note/all?type=md", name="文档", tag_code="md"),
            NoteTypeInfo(url="/note/all?type=gallery", name="相册", tag_code="gallery"),
            NoteTypeInfo(url="/note/all?type=list", name="清单", tag_code="list"),
            NoteTypeInfo(url="/note/all?type=table", name="表格", tag_code="table"),
            NoteTypeInfo(url="/note/removed", name="回收站", tag_code="removed", css_class="hide"),
        ]
    
class NoteCategory(NoteIndexDO):
    def __init__(self, code, name):
        self.name = f"{code}-{name}"
        self.url  = "/note/group?note_category=" + code
        self.icon = ""
        self.priority = 0
        self.level = 0
        self.is_deleted = 0
        self.size = 0
        self.show_next = True
        self.icon = "fa-folder"
        self.badge_info = ""
        self.tags = None

class NotePathInfo(Storage):

    def __init__(self, **kw):
        super().__init__()
        self.name = ""
        self.url = ""
        self.id = 0
        self.type = ""
        self.priority = 0
        self.is_public = 0
        self.update(kw)