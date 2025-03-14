# encoding=utf-8
import enum
import typing
import xutils

from xutils import Storage, EnumItem
from xutils import dateutil
from xnote.core import xtables
from xnote.core import xconfig
from xutils.db.dbutil_helper import new_from_dict
from xutils.base import EnumItem, BaseDataRecord

NOTE_ICON_DICT = {
    "group": "fa-folder",
    "md": "fa-file-text-o",
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

DEFAULT_ICON = "fa-file-text-o"


class NoteLevelEnum(xutils.BaseEnum):
    """笔记等级"""
    archived = EnumItem("归档", "-1")
    normal = EnumItem("普通", "0")
    sticky = EnumItem("置顶", "1")

class OrderTypeEnum(xutils.BaseEnum):
    """排序方式"""
    name = EnumItem("名称", "1")
    hot = EnumItem("热门", "2")
    size = EnumItem("大小", "3")
    ctime_desc = EnumItem("最新", "4")


class NoteIndexDO(BaseDataRecord):
    def __init__(self, **kw):
        super().__init__()
        now = dateutil.format_datetime()
        self.id = 0
        self.name = ""
        self.creator = ""
        self.creator_id = 0
        self.type = ""
        self.ctime = now # 创建时间
        self.mtime = now # 修改时间
        self.atime = now # 访问时间
        self.dtime = xtables.DEFAULT_DATETIME # 删除时间
        self.parent_id = 0 # 默认挂在根目录下
        self.size = 0
        self.children_count = 0
        self.version = 0
        self.is_deleted = 0
        self.is_public = 0
        self.level = 0 # 等级 (-1)-归档 0-正常, 1-置顶
        self.tag_str = ""
        self.visit_cnt = 0
        self.order_type = 0 # 排序方式
        self.update(kw)

    def handle_from_dict(self):
        self.compat_old()

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
        self.category = ""
        self.badge_info = ""
        self.show_next = False
        self.url = self.get_url()
        self.icon = NOTE_ICON_DICT.get(self.type, DEFAULT_ICON)

    def get_tags(self):
        return self.tag_str.split()
    
    def set_tags(self, tags=[]):
        self.tags = tags
        self.tag_str = " ".join(tags)

    @property
    def visited_cnt(self):
        return self.visit_cnt
    
    @property
    def archived(self):
        return self.level<0

    @property
    def hot_index(self):
        return self.visit_cnt
    
    @property
    def note_id(self):
        return self.id
    
    def is_group(self):
        return self.type == "group"
    
    def is_markdown(self):
        return self.type == "md"
    
    @property
    def is_sticky(self):
        """是否是置顶"""
        return self.level > 0
    
    def get_url(self):
        return f"{xconfig.WebConfig.server_home}/note/view/{self.id}"
    
    def get_edit_url(self):
        return f"{xconfig.WebConfig.server_home}/note/edit?id={self.id}"
    
class NoteDO(NoteIndexDO):
    def __init__(self, **kw):
        super(NoteDO, self).__init__()
        self.path = ""
        self.category = "" # 废弃
        self.content = ""
        self.data = ""
        self.token = ""
        self.priority = 0 # (-1):归档, 0-正常, 1-置顶
        self.tags = []
        self.orderby = "" # 废弃字段

        # 假的属性
        self.icon = ""
        self.show_edit = True
        self.badge_info = ""
        self.create_date = ""
        self.update_date = ""
        self.update(kw)

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

def del_dict_key(dict: dict, key):
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

class NoteToken(BaseDataRecord):
    def __init__(self, type="", id=0):
        self.type = type
        self.id = id
    
class NoteTypeInfo:

    def __init__(self, url="", name="", tag_code="", css_class=""):
        self.url = xconfig.WebConfig.server_home + url
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
            NoteTypeInfo(url="/note/comment/mine", name="评论", tag_code="comment"),
            NoteTypeInfo(url="/note/dict", name="词典",  tag_code="dict"),
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

class NoteGroupDO(NoteIndexDO):
    def __init__(self):
        self.children = []

class NoteOptGroup(Storage):
    def __init__(self):
        super(NoteOptGroup, self).__init__()
        self.label = ""
        self.children = [] # type: list[NoteIndexDO]

