# encoding=utf-8
import enum
import typing
import xutils

from typing import List, Optional
from xutils import Storage, EnumItem
from xutils import dateutil
from xnote.core import xtables
from xnote.core import xconfig
from xutils.db.dbutil_helper import new_from_dict
from xutils.base import EnumItem, BaseDataRecord
from xnote_handlers.note.constant import NoteType
from xnote.plugin import TextLink, TabBox, DataTable, Card
from xutils.functions import del_dict_key, delete_None_values
from xutils.fsutil import FileItem

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

class NoteTypeEnum(xutils.BaseEnum):
    """笔记类型枚举"""
    alias = NoteType(name="别名", type="alias")
    list = NoteType(name="清单", type="list")

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
        self.manual_short_desc = ""
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

    def before_save(self, index_do: "NoteDO"):
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
    
    def set_tags(self, tags: typing.List[str]=[]):
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
    
    @property
    def is_group(self):
        return self.type == "group"
    
    @property
    def is_markdown(self):
        return self.type == "md"
    
    @property
    def is_alias(self):
        return self.type == NoteTypeEnum.alias.value
    
    @property
    def original_note_id(self):
        """实际的note_id，如果是别名类型，返回真实的笔记ID，否则返回自身的note_id"""
        if self.is_alias:
            return self.parent_id
        return self.note_id
    
    @property
    def is_sticky(self):
        """是否是置顶"""
        return self.level > 0
    
    @property
    def is_pinned(self):
        """是否置顶"""
        return self.level > 0
    
    @property
    def is_list(self):
        return self.type == NoteTypeEnum.list.value
    
    @property
    def short_desc(self):
        return self.manual_short_desc
    
    def get_url(self):
        return f"{xconfig.WebConfig.server_home}/note/view/{self.id}"
    
    def get_edit_url(self):
        return f"{xconfig.WebConfig.server_home}/note/edit?id={self.id}"
    
    def _new_meta(self, meta_key: str, meta_value: str):
        meta = NoteMetaRecord()
        meta.note_id = self.note_id
        meta.user_id = self.creator_id
        meta.meta_key = meta_key
        meta.meta_value = meta_value
        return meta
    
    def to_meta_list(self, view_tab = "meta"):
        if view_tab == "all":
            return [
                self._new_meta("_manual_short_desc", self.manual_short_desc),
            ]
        return [
            self._new_meta("_type", self.type),
            self._new_meta("_create_date", dateutil.format_date(self.ctime)),
            self._new_meta("_manual_short_desc", self.manual_short_desc),
        ]
    
class NoteDO(NoteIndexDO):
    _virtual_fields = [
        "url", 
        "icon",
        "show_edit", 
        "create_date",
        "update_date",
        "badge_info",
        "tag_info_list",
    ]

    def __init__(self, **kw):
        super(NoteDO, self).__init__()
        self.path = ""
        self.category = "" # 废弃
        self.content = ""
        self.data = ""
        self.token = ""
        self.priority = 0 # (-1):归档, 0-正常, 1-置顶
        self.tags = [] # type: list[str]
        self.orderby = "" # 废弃字段

        # 假的属性
        self.icon = ""
        self.show_edit = True
        self.badge_info = ""
        self.create_date = ""
        self.update_date = ""
        self.share_time: typing.Optional[str] = None
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
        for key in self._virtual_fields:
            self.pop(key, None)
        delete_None_values(self)
        
    def update_from_index(self, note_index: NoteIndexDO):
        self.name = note_index.name
        self.ctime = note_index.ctime
        self.mtime = note_index.mtime
        self.atime = note_index.atime
        self.size = note_index.size
        self.parent_id = note_index.parent_id
        self.visit_cnt = note_index.visit_cnt
        self.children_count = note_index.children_count
        self.level = note_index.level
        self.creator_id = note_index.creator_id
        self.tag_str = note_index.tag_str
        self.tags = note_index.get_tags()
        self.order_type = note_index.order_type
        self.manual_short_desc = note_index.manual_short_desc


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
            NoteTypeInfo(url="/comment/mine", name="评论", tag_code="comment"),
            NoteTypeInfo(url="/note/dict", name="词典",  tag_code="dict"),
            NoteTypeInfo(url="/fs_upload/manage", name="文件", tag_code="file"),
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

    @classmethod
    def public_from_note_index(cls, index: NoteIndexDO):
        result = NotePathInfo()
        result.name = index.name
        result.is_public = True
        result.url = xconfig.WebConfig.resolve_path(f"/note/view/public?id={index.note_id}")
        result.id = index.id
        result.type = index.type
        result.priority = index.priority
        return result

class NoteGroupDO(NoteIndexDO):
    def __init__(self):
        self.children = []

class NoteOptGroup(Storage):
    def __init__(self, label = ""):
        self.label = label
        self.children = [] # type: list[NoteIndexDO]

    def add_note(self, note: NoteIndexDO):
        self.children.append(note)

class NoteRelationGroup(BaseDataRecord):

    def __init__(self, **kw):
        self.label = ""
        self.children = [] # type: list[TextLink]


class NoteVisitLogDO(BaseDataRecord):
    def __init__(self, **kw):
        self.id = 0
        self.note_id = 0
        self.user_id = 0
        self.visit_cnt = 0
        self.atime = dateutil.format_datetime()
        self.update(kw)


class NoteMetaRecord(BaseDataRecord):
    _ignore_save_fields = ["meta_id", "meta_name", "value_type", "meta_category"]
    def __init__(self):
        current_ms = dateutil.timestamp_ms()
        self.meta_id = 0
        self.create_time = current_ms
        self.update_time = current_ms
        self.version = 0
        self.note_id = 0
        self.user_id = 0
        self.meta_key = ""
        self.meta_value = ""
        self.index_value: Optional[str] = None
        
        # 虚拟字段
        self.meta_name = ""
        self.value_type = ""
        self.meta_category = ""
        
    def validate(self):
        if self.note_id <= 0:
            raise Exception("invalid note_id")
        if self.user_id <= 0:
            raise Exception("invalid user_id")
        if self.meta_key == "":
            raise Exception("invalid meta_key")

class NoteViewContext(Storage):

    note_detail_tab: TabBox
    meta_tab: TabBox
    meta_table: DataTable
    filelist: List[FileItem]
    note_fragment: Card

    def __init__(self, **kw):
        self.user_name = ""
        self.user_id = 0
        self.recommended_notes = [] # type: list|object
        self.next_note = None # type: NoteIndexDO|None
        self.prev_note = None # type: NoteIndexDO|None
        
        self.can_edit = False
        self.show_left = False
        self.show_groups = False
        self.show_aside = True
        self.show_right = True
        self.show_contents_btn = False
        self.show_comment_edit = False
        self.show_comment = True
        self.show_content = True
        self.show_ext_info = True
        self.show_nav = True
        self.show_relation = False
        self.show_relation_row = True
        self.show_tag = True
        self.show_search_div = True
        self.show_parent_link = True
        self.show_alias = True
        # 元数据管理页面
        self.show_meta_manage = False
        self.show_gallery = False

        self.page = 1
        self.pagesize = 20
        self.page_max = 1
        self.page_url = ""

        self.groups = []
        self.files = []
        self.show_mdate = False
        self.show_add_file = False
        self.template_name = "note/page/detail/note_detail.html"
        self.search_type = "note"
        self.comment_source_class = "hide"
        self.op = ""
        self.is_public_page = False
        self.OrderTypeEnum = OrderTypeEnum
        self.file = None # type: NoteIndexDO|None
        self.parent_id = 0
        self.content = ""
        self.note_alias_list = [] # type: list[NoteIndexDO]
        self.show_recommend = False
        self.show_pagination = False
        self.edit_token = ""
        self.tab = ""
        self.create_btn_text = ""
        self.relation_group_list = None # type: None|list[NoteRelationGroup]
        self.related_notes = [] # type: list[TextLink]
        self.relation_table = None # type: DataTable|None
        self.rev_relation_table = None # type: DataTable|None
        self.note_group_list = [] # type: list[NoteOptGroup]
        self.q_tag = ""
        self.note_meta_list: List[NoteMetaRecord] = []
    
        self.update(kw)

    def hide_components(self):
        self.show_comment = False
        self.show_comment_edit = False
        self.show_content = False
        self.show_relation = False
        self.show_relation_row = False
        self.show_ext_info = False
        self.show_tag = False
        self.show_alias = False
        self.show_gallery = False
        
    def update_detail_tab(self):
        note_tab = TabBox(tab_key="tab", tab_default="all", css_class="btn-style")
        note_tab.add_item(title="全部", value="all")
        if not self.is_public_page:
            note_tab.add_item(title="关联笔记", value="relation")
            note_tab.add_item(title="元数据", value="meta")
        if not self.is_list_type:
            note_tab.add_item(title="评论", value="comment")
        self.note_detail_tab = note_tab

    @property
    def note_id(self):
        if self.file:
            return self.file.note_id
        return 0
    
    @property
    def is_list_type(self):
        if self.file:
            return self.file.is_list
        return False

class FragmentType:
    event = "event"

class NoteFragmentRecord(BaseDataRecord):
    _ignore_save_fields = ["frag_id"]
    
    def __init__(self):
        super().__init__()
        self.frag_id = 0
        self.create_time = 0
        self.update_time = 0
        self.sort_num = 0
        self.date_text = ""
        self.date_sort = 0
        self.date_precision = 0
        self.frag_type = FragmentType.event
        self.frag_status = 1
        self.content = ""
        self.meta = ""
        self.note_id = 0
        self.user_id = 0
        self.file_ids = ""
        
        
        