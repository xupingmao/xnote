# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2022/03/16 19:07:21
# @filename dao.py

"""资料的DAO操作集合
DAO层只做最基础的数据库交互，不做权限校验（空校验要做），业务状态检查之类的工作

一些表的说明
note_full:<note_id>              = 笔记的内容，包含一些属性（部分属性比如访问时间、访问次数不是实时更新的）
note_index:<note_id>             = 笔记索引，不包含内容
note_tiny:<user>:<note_id>       = 用户维度的笔记索引
notebook:<user>:<note_id>        = 用户维度的笔记本(项目)索引
token:<uuid>                     = 用于链接分享的令牌
note_history:<note_id>:<version> = 笔记的历史版本
note_comment:<note_id>:<timeseq> = 笔记的评论
comment_index:<user>:<timeseq>   = 用户维度的评论索引
search_history:<id>  = 用户维度的搜索历史
note_public:<note_id>            = 公开的笔记索引
"""
import time
import os
import xconfig
import xutils
import xmanager
import logging
import xauth
import pdb
from xutils import Storage
from xutils import dateutil, dbutil, textutil, fsutil
from xutils import cacheutil
from .dao_api import NoteDao
from . import dao_log

def register_note_table(name, description, check_user=False, user_attr=None):
    dbutil.register_table(name, description, category="note",
                          check_user=check_user, user_attr=user_attr)
    
register_note_table("notebook", "笔记分组", check_user=True, user_attr="creator")
register_note_table("token", "用于分享的令牌")
register_note_table("note_history", "笔记的历史版本")

NOTE_DAO = xutils.DAO("note")

_full_db = dbutil.get_table("note_full")
_tiny_db = dbutil.get_table("note_tiny")
_index_db = dbutil.get_table("note_index")
_book_db = dbutil.get_table("notebook")
_search_history_db = dbutil.get_table("search_history")

_note_history_db = dbutil.get_hash_table("note_history")
_note_history_index_db = dbutil.get_hash_table("note_history_index")
_public_db = dbutil.get_table("note_public")
_token_db = dbutil.get_table("token")

DB_PATH = xconfig.DB_PATH
MAX_STICKY_SIZE = 1000
MAX_SEARCH_SIZE = 1000
MAX_SEARCH_KEY_LENGTH = 20
MAX_LIST_SIZE = 1000
_cache = cacheutil.PrefixedCache("note:")

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

class NoteDO(Storage):
    def __init__(self):
        self.id = "" # id是str
        self.name = ""
        self.path = ""
        self.creator = ""
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.atime = dateutil.format_datetime()
        self.type = "md"
        self.category = "" # 废弃
        self.size = 0
        self.children_count = 0
        self.parent_id = "0" # 默认挂在根目录下
        self.content = ""
        self.data = ""
        self.is_deleted = 0 # 0-正常， 1-删除
        self.is_public = 0  # 0-不公开, 1-公开
        self.token = ""
        self.priority = 0 # 1-正常
        self.visited_cnt = 0
        self.orderby = ""
        # 热门指数
        self.hot_index = 0
        # 版本
        self.version = 0

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

def remove_virtual_fields(note):
    del_dict_key(note, "url")
    del_dict_key(note, "icon")
    del_dict_key(note, "show_edit")
    del_dict_key(note, "create_date")
    del_dict_key(note, "badge_info")
    del_dict_key(note, "create_date")
    del_dict_key(note, "update_date")
    del_dict_key(note, "tag_info_list")


def format_note_id(id):
    return str(id)


def format_date(date):
    if date is None:
        return date
    return date.split(" ")[0].replace("-", "/")


def get_root(creator=None):
    if creator == None:
        creator = xauth.current_name()

    assert creator != None
    root = NoteDO()
    root.creator = creator
    root.name = "根目录"
    root.type = "group"
    root.parent_id = "0"
    build_note_info(root)
    root.url = "/note/group"
    return root


def is_root_id(id):
    return id in (None, "", "0", 0)


def get_default_group():
    group = NoteDO()
    group.name = "默认分组"
    group.type = "group"
    group.id = "default"
    group.parent_id = "0"
    build_note_info(group)
    group.url = "/note/default"
    return group


def get_archived_group():
    group = NoteDO()
    group.name = "归档分组"
    group.type = "group"
    group.id = "archived"
    group.parent_id = "0"
    group.content = ""
    group.priority = 0
    build_note_info(group)
    group.url = "/note/archived"
    return group

def get_note_public_table():
    return _public_db


def get_note_tiny_table(user_name):
    return dbutil.get_table("note_tiny", user_name=user_name)


def batch_query(id_list):
    result = dict()
    for id in id_list:
        note = _index_db.get_by_id(id)
        if note:
            result[id] = note
            build_note_info(note)
    return result


def batch_query_list(id_list):
    result = []
    batch_result = _index_db.batch_get_by_id(id_list)
    for id in batch_result:
        note = batch_result.get(id)
        if note:
            build_note_info(note)
            result.append(note)
    return result


def sort_by_name(notes):
    notes.sort(key=lambda x: x.name)
    sort_by_priority(notes)


def sort_by_name_desc(notes):
    notes.sort(key=lambda x: x.name, reverse=True)
    sort_by_priority(notes)


def sort_by_name_priority(notes):
    sort_by_name(notes)
    sort_by_priority(notes)


def sort_by_mtime_desc(notes):
    notes.sort(key=lambda x: x.mtime, reverse=True)


def sort_by_ctime_desc(notes):
    notes.sort(key=lambda x: x.ctime, reverse=True)
    sort_by_priority(notes)


def sort_by_atime_desc(notes):
    notes.sort(key=lambda x: x.atime, reverse=True)


def sort_by_priority(notes):
    # 置顶笔记
    notes.sort(key=lambda x: x.priority, reverse=True)


def sort_by_default(notes):
    # 先按照名称排序
    sort_by_name(notes)

    # 置顶笔记
    sort_by_priority(notes)

    # 文件夹放在前面
    sort_by_type(notes)


def sort_by_ctime_priority(notes):
    # 先按照名称排序
    sort_by_ctime_desc(notes)

    # 置顶笔记
    sort_by_priority(notes)

    # 文件夹放在前面
    sort_by_type(notes)


def sort_by_type(notes):
    # 文件夹放在前面
    notes.sort(key=lambda x: 0 if x.type == "group" else 1)


def sort_by_type_mtime_desc(notes):
    sort_by_mtime_desc(notes)
    sort_by_type(notes)


def sort_by_type_ctime_desc(notes):
    sort_by_ctime_desc(notes)
    sort_by_type(notes)


def sort_by_dtime_desc(notes):
    notes.sort(key=lambda x: x.dtime, reverse=True)


def sort_by_dtime_asc(notes):
    notes.sort(key=lambda x: x.dtime)


def sort_by_hot_index(notes):
    notes.sort(key=lambda x: x.hot_index or 0, reverse=True)
    sort_by_priority(notes)

    for note in notes:
        note.badge_info = "热度(%d)" % note.hot_index

def sort_by_size_desc(notes):
    notes.sort(key=lambda x:x.size or 0, reverse=True)
    sort_by_priority(notes)
    
    for note in notes:
        note.badge_info = "%s" % note.size

SORT_FUNC_DICT = {
    "name": sort_by_name,
    "name_asc": sort_by_name,
    "name_desc": sort_by_name_desc,
    "name_priority": sort_by_name_priority,
    "mtime_desc": sort_by_mtime_desc,
    "ctime_desc": sort_by_ctime_desc,
    "ctime_priority": sort_by_ctime_priority,
    "atime_desc": sort_by_atime_desc,
    "type_mtime_desc": sort_by_type_mtime_desc,
    "type_ctime_desc": sort_by_type_ctime_desc,
    "dtime_desc": sort_by_dtime_desc,
    "dtime_asc": sort_by_dtime_asc,
    "hot_index": sort_by_hot_index,
    "hot_desc": sort_by_hot_index,
    "size_desc": sort_by_size_desc,
    "default": sort_by_default,
}


def sort_notes(notes, orderby="name"):
    if orderby is None:
        orderby = "name"

    sort_func = SORT_FUNC_DICT.get(orderby, sort_by_mtime_desc)
    build_note_list_info(notes, orderby)
    sort_func(notes)


def build_note_list_info(notes, orderby=None):
    for note in notes:
        build_note_info(note, orderby)


def build_note_info(note, orderby=None):
    if note is None:
        return None

    # note.url = "/note/view?id={}".format(note["id"])
    note.url = "/note/view/{}".format(note["id"])
    if note.priority is None:
        note.priority = 0

    if note.content is None:
        note.content = ''

    if note.data is None:
        note.data = ''
    # process icon
    note.icon = NOTE_ICON_DICT.get(note.type, "fa-file-text-o")
    note.id = str(note.id)

    if note.type in ("list", "csv"):
        note.show_edit = False

    if note.visited_cnt is None:
        note.visited_cnt = 0

    if note.orderby is None:
        note.orderby = "ctime_desc"

    if note.category is None:
        note.category = "000"

    if note.hot_index is None:
        note.hot_index = 0

    if note.ctime != None:
        note.create_date = format_date(note.ctime)

    if note.mtime != None:
        note.update_date = format_date(note.mtime)

    # 处理删除时间
    if note.is_deleted == 1 and note.dtime == None:
        note.dtime = note.mtime

    if orderby == "hot_index":
        note.badge_info = "热度: %s" % note.hot_index
    
    if orderby == "mtime_desc":
        note.badge_info = format_date(note.mtime)

    if note.badge_info is None:
        note.badge_info = note.create_date

    if note.type == "group":
        _build_book_default_info(note)

    from . import dao_tag
    dao_tag.handle_tag_for_note(note)

    return note


def _build_book_default_info(note):
    if note.children_count == None:
        note.children_count = 0


def convert_to_path_item(note):
    return Storage(name=note.name, url=note.url, id=note.id,
                   type=note.type, priority=note.priority, is_public=note.is_public)


@xutils.timeit(name="NoteDao.ListPath:leveldb", logfile=True)
def list_path(file, limit=5):
    assert file != None

    pathlist = []
    while file is not None:
        pathlist.insert(0, convert_to_path_item(file))
        file.url = "/note/%s" % file.id
        if len(pathlist) >= limit:
            break
        if str(file.id) == "0":
            break

        parent_id = str(file.parent_id)
        # 处理根目录
        if parent_id == "0":
            if file.type != "group":
                pathlist.insert(0, get_default_group())
            elif file.archived:
                pathlist.insert(0, get_archived_group())
            pathlist.insert(0, convert_to_path_item(get_root(file.creator)))
            break

        file = get_by_id(parent_id, include_full=False)
    return pathlist


def get_full_by_id(id):
    if isinstance(id, int):
        id = str(id)
    return _full_db.get_by_id(id)


@xutils.timeit(name="NoteDao.GetById:leveldb", logfile=True)
def get_by_id(id, include_full=True, creator=None):
    if id == "" or id is None:
        return None
    id = str(id)
    if id == "0":
        return get_root(creator)

    note_index = _index_db.get_by_id(id)
    if note_index != None:
        note_index = NoteDO.from_dict(note_index)

    if not include_full and note_index != None:
        build_note_info(note_index)
        return note_index

    note = get_full_by_id(id)
    if note != None:
        note = NoteDO.from_dict(note)
    
    if note and not include_full:
        del note.content
        del note.data

    if note != None and note_index != None:
        note.name = note_index.name
        note.mtime = note_index.mtime
        note.atime = note_index.atime
        note.size = note_index.size
        note.tags = note_index.tags
        note.parent_id = note_index.parent_id
        note.visited_cnt = note_index.visited_cnt
        note.hot_index = note_index.hot_index
        note.children_count = note_index.children_count
        note.path = note_index.path

    build_note_info(note)
    return note

def get_by_id_creator(id, creator, db=None):
    note = get_by_id(id, creator=creator)
    if note and note.creator == creator:
        return note
    return None


def get_by_token(token):
    token_info = _token_db.get_by_id(token)
    if token_info != None and token_info.type == "note":
        return get_by_id(token_info.id)
    return None


def get_by_user_skey(user_name, skey):
    skey = skey.replace("-", "_")
    note_info = _index_db.first_by_index("skey", where = dict(creator=user_name, skey=skey))
    if note_info != None:
        note_info = NoteDO.from_dict(note_info)
        return get_by_id(note_info.id)
    else:
        return None

def delete_note_skey(note):
    # 使用的是note_index的索引,不需要处理
    pass


def get_or_create_note(skey, creator):
    """根据skey查询或者创建笔记
    @param {string} skey 笔记的特殊key，用户维度唯一
    @param {string} creator 笔记的创建者
    @throws {exception} 创建异常
    """
    if skey is None or skey == "":
        return None
    skey = skey.replace("-", "_")

    note = get_by_user_skey(creator, skey)
    if note != None:
        return note

    # 检查笔记名称
    check_by_name(creator, skey)

    note_dict = Storage()
    note_dict.name = skey
    note_dict.skey = skey
    note_dict.creator = creator
    note_dict.content = ""
    note_dict.data = ""
    note_dict.type = "md"
    note_dict.sub_type = "log"
    note_dict.parent_id = "0"

    note_id = create_note(note_dict)

    return get_by_id(note_id)


def create_note_base(note_dict, date_str=None, note_id=None):
    """创建笔记的基础部分，无锁"""
    # 真实的创建时间
    ctime0 = dateutil.format_datetime()
    note_dict["ctime0"] = ctime0
    note_dict["atime"] = ctime0
    note_dict["mtime"] = ctime0
    note_dict["ctime"] = ctime0
    note_dict["version"] = 1

    if note_id is not None:
        # 指定id创建笔记
        note_dict["id"] = note_id
        put_note_to_db(note_id, note_dict)
        # 创建日志
        add_create_log(note_dict)
        return note_id
    elif date_str is None or date_str == "":
        # 默认创建规则
        note_id = _index_db.insert(note_dict)
        note_dict["id"] = note_id
        put_note_to_db(note_id, note_dict)
        # 创建日志
        add_create_log(note_dict)
        return note_id
    else:
        # 指定日期创建
        date_str = date_str.replace(".", "-")
        if date_str == dateutil.format_date():
            # 当天创建的，保留秒级
            timestamp = int(time.time() * 1000)
        else:
            timestamp = int(dateutil.parse_date_to_timestamp(date_str) * 1000)

        note_dict["ctime"] = dateutil.format_datetime(timestamp/1000)
        note_id = _index_db.insert(note_dict)
        note_dict["id"] = note_id
        put_note_to_db(note_id, note_dict)

        # 创建日志
        add_create_log(note_dict)
        return note_id


def is_not_empty(value):
    return xutils.is_str(value) and value != ""


def create_note(note_dict, date_str=None, note_id=None, check_name=True):
    content = note_dict["content"]
    creator = note_dict["creator"]
    name = note_dict.get("name")

    assert is_not_empty(name), "笔记名称不能为空"

    if "parent_id" not in note_dict:
        note_dict["parent_id"] = "0"
    if "priority" not in note_dict:
        note_dict["priority"] = 0
    if "data" not in note_dict:
        note_dict["data"] = ""
    if "category" not in note_dict:
        note_dict["category"] = "000"

    with dbutil.get_write_lock(name):
        # 检查名称是否冲突
        if check_name:
            check_by_name(creator, name)

        # 创建笔记的基础信息
        note_id = create_note_base(note_dict, date_str, note_id)
    
    if content != "":
        # 如果内部不为空，创建一个历史记录
        add_history(note_id, note_dict["version"], note_dict)

    # 更新分组下面页面的数量
    update_children_count(note_dict["parent_id"])

    # 创建对应的文件夹
    if type == "gallery":
        dirname = os.path.join(xconfig.UPLOAD_DIR, creator, str(note_id))
        xutils.makedirs(dirname)

    # 更新目录修改时间
    touch_note(note_dict["parent_id"])

    # 最后发送创建笔记成功的消息
    create_msg = dict(name=name, type=type, id=note_id)
    xmanager.fire("note.add", create_msg)
    xmanager.fire("note.create", create_msg)

    return note_id


def create_token(type, note_id=""):
    uuid = textutil.generate_uuid()
    token_info = Storage(type=type, id=note_id)
    dbutil.put("token:%s" % uuid, token_info)
    return uuid


def add_create_log(note):
    dao_log.add_create_log(note.creator, note)


def add_visit_log(user_name, note):
    dao_log.add_visit_log(user_name, note)


def put_note_to_db(note_id, note):
    creator = note.creator
    # 增加编辑日志
    dao_log.add_edit_log(creator, note)

    # 删除不需要持久化的数据
    remove_virtual_fields(note)

    # 保存到DB
    _full_db.update_by_id(note_id, note)

    # 更新索引
    update_index(note)

def touch_note(note_id):
    if is_root_id(note_id):
        return

    note = get_by_id(note_id)
    if note != None:
        note.mtime = dateutil.format_datetime()
        update_index(note)


def del_dict_key(dict, key):
    if key in dict:
        del dict[key]


def convert_to_index(note):
    note_index = Storage(**note)

    # 删除虚拟字段
    remove_virtual_fields(note_index)

    # 删除内容字段
    del_dict_key(note_index, 'data')
    del_dict_key(note_index, 'content')

    note_index.parent_id = str(note_index.parent_id)

    return note_index


def update_index(note):
    """更新索引的时候也会更新用户维度的索引(note_tiny)"""
    id = note['id']
    note_id = format_note_id(id)

    if is_root_id(id):
        # 根目录，不需要更新
        return
        
    note_index = convert_to_index(note)
    _index_db.update_by_id(note_id, note_index)

    # 更新用户维度的笔记索引
    note_tiny_db = get_note_tiny_table(note.creator)
    note_tiny_db.update_by_id(note_id, note_index)

    if note.type == "group":
        _book_db.update_by_id(note_id, note_index, user_name=note.creator)

    if note.is_public != None:
        update_public_index(note)


def update_public_index(note):
    db = get_note_public_table()
    note_id = format_note_id(note.id)

    if note.is_public:
        note_index = convert_to_index(note)
        db.update_by_id(note_id, note_index)
    else:
        db.delete_by_id(note_id)


def update_note(note_id, **kw):
    # 这里只更新基本字段，移动笔记使用 move_note
    logging.info("update_note, note_id=%s, kw=%s", note_id, kw)

    parent_id = kw.get("parent_id")
    content = kw.get('content')
    data = kw.get('data')
    priority = kw.get('priority')
    name = kw.get("name")
    atime = kw.get("atime")
    is_public = kw.get("is_public")
    tags = kw.get("tags")
    orderby = kw.get("orderby")
    archived = kw.get("archived")
    size = kw.get("size")
    token = kw.get("token")
    visited_cnt = kw.get("visited_cnt")

    note = get_by_id(note_id)
    if note is None:
        raise Exception("笔记不存在,id=%s" % note_id)
    
    if parent_id != None and parent_id != note.parent_id:
        raise Exception(
            "[note.dao.update_note] can not update `parent_id`, please use `note.dao.move_note`")

    if content:
        note.content = content
    if data:
        note.data = data
    if priority != None:
        note.priority = priority
    if name:
        note.name = name
    if atime:
        note.atime = atime

    # 分享相关的更新
    if is_public != None:
        note.is_public = is_public
    if is_public == 1:
        note.share_time = dateutil.format_time()
    if is_public == 0:
        note.share_time = None

    if tags != None:
        note.tags = tags
    if orderby != None:
        note.orderby = orderby
    if archived != None:
        note.archived = archived
    if size != None:
        note.size = size
    if token != None:
        note.token = token
    if visited_cnt != None:
        note.visited_cnt = visited_cnt

    if note.version is None:
        note.version = 1

    old_version = note.version
    note.mtime = xutils.format_time()
    note.version += 1

    # 只修改优先级
    if len(kw) == 1 and kw.get('priority') != None:
        note.version = old_version
    # 只修改名称
    if len(kw) == 1 and kw.get('name') != None:
        note.version = old_version

    put_note_to_db(note_id, note)
    return 1


def move_note(note, new_parent_id):
    # type: (Storage, str) -> None
    assert isinstance(new_parent_id, str)
    assert len(new_parent_id) > 0

    old_parent_id = note.parent_id
    note.parent_id = new_parent_id

    if old_parent_id == new_parent_id:
        return
    
    new_parent = get_by_id(new_parent_id)
    
    if new_parent != None:
        parent_path = new_parent.path or new_parent.name
        assert parent_path != None
        note.path = parent_path + " - " + note.name
    
    # 没有更新内容，只需要更新索引数据
    note.mtime = dateutil.format_datetime()
    update_index(note)

    # 更新文件夹的容量
    update_children_count(old_parent_id)
    update_children_count(new_parent_id, parent_note=new_parent)

    # 更新新的parent更新时间
    touch_note(new_parent_id)


def update0(note):
    """更新基本信息，比如name、mtime、content、items、priority等,不处理parent_id更新"""
    current = get_by_id(note.id)
    if current is None:
        return
    # 更新各种字段
    current_time = xutils.format_datetime()
    note.version = current.version + 1
    note.mtime = current_time
    note.atime = current_time
    put_note_to_db(note.id, note)


def get_by_name(creator, name):
    assert creator != None, "get_by_name:creator is None"
    assert name != None, "get_by_name: name is None"

    db = get_note_tiny_table(creator)
    result = db.list(offset=0, limit=1, where = dict(name=name))
    result = list(filter(lambda x: not x.is_deleted, result))
    if len(result) > 0:
        note = result[0]
        return get_by_id(note.id)
    return None


def check_by_name(creator, name):
    note_by_name = get_by_name(creator, name)
    if note_by_name != None:
        raise Exception("笔记【%s】已存在" % name)


def visit_note(user_name, id):
    note = get_by_id(id)
    if note is None:
        return

    note.atime = xutils.format_datetime()
    # 访问的总字数
    if note.visited_cnt is None:
        note.visited_cnt = 0
    note.visited_cnt += 1
    note.visit_cnt = note.visited_cnt

    # 全局访问热度
    if note.hot_index is None:
        note.hot_index = 0
    note.hot_index += 1

    add_visit_log(user_name, note)
    update_index(note)


def update_children_count(parent_id, db=None, parent_note=None):
    if is_root_id(parent_id):
        return

    if parent_note == None:
        parent_note = get_by_id(parent_id)
    
    if parent_note is None:
        return

    creator = parent_note.creator
    count = 0
    for child in list_by_parent(creator, parent_id):
        if child.type == "group":
            count += child.children_count or 0
        else:
            count += 1

    parent_note.children_count = count
    update_index(parent_note)


def fill_parent_name(files):
    id_list = []
    for item in files:
        build_note_info(item)
        id_list.append(item.parent_id)

    note_dict = batch_query(id_list)
    for item in files:
        parent = note_dict.get(item.parent_id)
        if parent != None:
            item.parent_name = parent.name
        else:
            item.parent_name = None


def check_group_status(status):
    if status is None:
        return
    if status not in ("all", "active", "archived"):
        raise Exception("[check_group_status] invalid status: %s" % status)


@xutils.timeit(name="NoteDao.ListGroup:leveldb", logfile=True)
def list_group_with_count(creator=None,
               orderby="mtime_desc",
               skip_archived=False,
               status="all", **kw):
    """查询笔记本列表"""

    offset = kw.get("offset", 0)
    limit = kw.get("limit", 1000)
    parent_id = kw.get("parent_id")
    category = kw.get("category") 
    tags = kw.get("tags")
    search_name = kw.get("search_name")
    count_total = kw.get("count_total", False)
    count_only = kw.get("count_only", False)

    assert creator != None
    check_group_status(status)

    if category == "" or category == "all":
        category = None

    q_tags = tags
    if tags != None and len(tags) == 0:
        q_tags = None

    q_name = search_name
    if q_name == "":
        q_name = None

    if q_name != None:
        q_name = q_name.lower()

    # TODO 添加索引优化
    def list_group_func(key, value):
        if value.type != "group" or value.is_deleted:
            return False

        if skip_archived and value.archived:
            return False

        if parent_id != None and value.parent_id != parent_id:
            return False

        if category != None and value.category != category:
            return False

        if q_tags != None:
            if not isinstance(value.tags, list):
                return False
            if not textutil.contains_any(value.tags, q_tags):
                return False

        if q_name != None:
            if q_name not in value.name.lower():
                return False

        if status == "archived":
            return value.archived

        if status == "active":
            return not value.archived

        return True

    if count_only:
        return [], _book_db.count(user_name=creator, filter_func=list_group_func)

    notes = _book_db.list(
        user_name=creator, filter_func=list_group_func, limit=limit)
    sort_notes(notes, orderby)
    result = notes[offset:offset + limit]

    if count_total:
        if len(notes) < limit:
            return result, len(notes)
        return result, _book_db.count(user_name=creator, filter_func=list_group_func)
    else:
        return result, 0


def list_group(*args, **kw):
    list, count = list_group_with_count(*args, **kw)
    if kw.get("count_only") == True:
        return count
    if kw.get("count_total") == True:
        return list, count
    return list

@cacheutil.kw_cache_deco(prefix="note.count_group")
def count_group(creator, status=None):
    check_group_status(status)
    value = count_group_by_db(creator, status)
    return value


def count_group_by_db(creator, status=None):
    if status is None:
        return _book_db.count(user_name=creator)

    data, count = list_group_with_count(creator, status = status, count_only=True)
    return count


@xutils.timeit(name="NoteDao.ListRootGroup:leveldb", logfile=True)
def list_root_group(creator=None, orderby="name"):
    def list_root_group_func(key, value):
        return value.creator == creator and value.type == "group" \
            and value.parent_id in (0,"0") and value.is_deleted == 0

    notes = _book_db.list(user_name=creator, filter_func = list_root_group_func)
    sort_notes(notes, orderby)
    return notes


def list_default_notes(creator, offset=0, limit=1000, orderby="mtime_desc"):
    # TODO 添加索引优化
    def list_default_func(key, value):
        if value.is_deleted:
            return False
        if value.type == "group":
            return False
        return value.creator == creator and str(value.parent_id) == "0"

    notes = _tiny_db.list(filter_func = list_default_func)
    sort_notes(notes, orderby)
    return notes[offset:offset+limit]


def list_public(offset, limit, orderby="ctime_desc"):
    if orderby == "hot":
        index_name = "hot_index"
    else:
        index_name = "share_time"

    public_notes = _public_db.list_by_index(index_name,
                             offset=offset, limit=limit, reverse=True)

    build_note_list_info(public_notes)

    note_ids = []
    for note in public_notes:
        assert isinstance(note, Storage)
        note_ids.append(note.id)

    batch_result = _index_db.batch_get_by_id(note_ids)

    for note in public_notes:
        assert isinstance(note, Storage)
        note_info = batch_result.get(note.id)
        if note.is_deleted or note_info == None:
            logging.warning("笔记已删除:%s,name:%s", note.id, note.name)
            _public_db.delete(note)
        
        if note_info != None and not note_info.is_public:
            # FIX 历史数据
            logging.warning("分享状态不匹配: %s", note.id)
            _public_db.delete(note)

    return public_notes


def count_public():
    db = get_note_public_table()
    return db.count()


@xutils.timeit_deco(name="NoteDao.ListNote:leveldb", logfile=True, logargs=True)
def list_by_parent(creator, parent_id="", offset=0, limit=1000,
                   orderby="name",
                   skip_group=False,
                   include_public=True,
                   *,
                   tags=None):
    """通过父级节点ID查询笔记列表"""
    if parent_id is None:
        raise Exception("list_by_parent: parent_id is None")

    # 只要一个标签匹配即可
    q_tags = tags
    if q_tags != None and len(q_tags) == 0:
        q_tags = None

    parent_id = str(parent_id)
    # TODO 添加索引优化

    def list_note_func(key, value):
        if value.is_deleted:
            return False
        if skip_group and value.type == "group":
            return False
        if str(value.parent_id) != parent_id:
            return False

        if q_tags != None:
            if value.tags == None:
                return False
            if not textutil.contains_any(value.tags, q_tags):
                return False

        if include_public:
            return (value.is_public or value.creator == creator)
        else:
            return value.creator == creator

    notes = _tiny_db.list_by_index("parent_id", index_value=parent_id,
                                   offset=0, limit=limit, filter_func=list_note_func, user_name=creator)

    if orderby == "db":
        note = get_by_id_creator(parent_id, creator)
        if note == None:
            raise Exception("笔记不存在:%s" % parent_id)
        orderby = note.orderby

    sort_notes(notes, orderby)
    return notes[offset:offset+limit]


def list_by_date(field, creator, date, orderby="ctime_desc"):
    user = creator
    if user is None:
        user = "public"

    def list_func(key, value):
        if value.is_deleted:
            return False
        return date in getattr(value, field)

    files = dbutil.prefix_list("note_tiny:%s" % user, list_func)
    fill_parent_name(files)
    sort_notes(files, orderby)
    return files


@xutils.timeit(name="NoteDao.CountNote", logfile=True, logargs=True, logret=True)
def count_by_creator(creator):
    def count_func(key, value):
        if value.is_deleted:
            return False
        return value.creator == creator and type != 'group'
    return dbutil.prefix_count("note_tiny:%s" % creator, count_func)


def count_user_note(creator):
    return count_by_creator(creator)


def count_ungrouped(creator):
    return count_by_parent(creator, 0)


@xutils.timeit(name="NoteDao.CountNoteByParent", logfile=True, logargs=True, logret=True)
def count_by_parent(creator, parent_id):
    """统计笔记数量
    @param {string} creator 创建者
    @param {string|number} parent_id 父级节点ID
    """
    # TODO 添加索引优化
    parent_id_str = str(parent_id)

    def list_note_func(key, value):
        if value.is_deleted:
            return False
        return (value.is_public or value.creator == creator) and str(value.parent_id) == parent_id_str

    return _tiny_db.count(filter_func=list_note_func, user_name=creator)


@xutils.timeit(name="NoteDao.CountDict", logfile=True, logargs=True, logret=True)
def count_dict(user_name):
    import xtables
    return xtables.get_dict_table().count()


@xutils.timeit(name="NoteDao.FindPrev", logfile=True)
def find_prev_note(note, user_name):
    parent_id = str(note.parent_id)
    note_name = note.name

    def find_prev_func(key, value):
        if value.is_deleted:
            return False
        return str(value.parent_id) == parent_id and value.name < note_name
    result = dbutil.prefix_list("note_tiny:%s" % user_name, find_prev_func)
    result.sort(key=lambda x: x.name, reverse=True)
    if len(result) > 0:
        return result[0]
    else:
        return None


@xutils.timeit(name="NoteDao.FindNext", logfile=True)
def find_next_note(note, user_name):
    parent_id = str(note.parent_id)
    note_name = note.name

    def find_next_func(key, value):
        if value.is_deleted:
            return False
        return str(value.parent_id) == parent_id and value.name > note_name
    result = dbutil.prefix_list("note_tiny:%s" % user_name, find_next_func)
    result.sort(key=lambda x: x.name)
    # print([x.name for x in result])
    if len(result) > 0:
        return result[0]
    else:
        return None


def add_history_index(id, version, new_note):
    brief = Storage()
    brief.note_id = id
    brief.name = new_note.get("name")
    brief.version = version
    brief.mtime = new_note.get("mtime")

    version_str = str(version)
    _note_history_index_db.with_user(id).put(version_str, brief)

def add_history(note_id, version, new_note):
    # type: (str, int, dict) -> None
    """version是新的版本"""
    assert version != None

    # 先记录索引
    add_history_index(note_id, version, new_note)

    version_str = str(version)
    note_copy = dict(**new_note)
    note_copy['note_id'] = note_id
    _note_history_db.with_user(note_id).put(version_str, note_copy)

def list_history(note_id, limit=1000):
    """获取笔记历史的列表"""
    result_list = _note_history_index_db.with_user(note_id).list(limit=limit, reverse = True)
    history_list = [y for x,y in result_list]
    history_list = sorted(
        history_list, key=lambda x: x.mtime or "", reverse=True)
    return history_list

def delete_history(note_id, version=None):
    pass


def get_history(note_id, version):
    """获取笔记历史的详情"""
    note_id = str(note_id)
    version_str = str(version)
    return _note_history_db.with_user(note_id).get(version_str)


def search_name(words, creator=None, parent_id=None, orderby="hot_index"):
    # TODO 搜索排序使用索引
    assert isinstance(words, list)

    words = [word.lower() for word in words]
    if parent_id != None and parent_id != "":
        parent_id = str(parent_id)

    def search_func(key, value):
        if value.is_deleted:
            return False
        if parent_id != None and str(value.parent_id) != parent_id:
            return False
        is_user_match = (value.creator == creator or value.is_public)
        is_words_match = textutil.contains_all(value.name.lower(), words)
        return is_user_match and is_words_match

    db = get_note_tiny_table(creator)

    result = db.list(filter_func=search_func,
                     offset=0, limit=MAX_SEARCH_SIZE, fill_cache=False)

    # 补全信息
    build_note_list_info(result)

    # 对笔记进行排序
    sort_notes(result, orderby)
    sort_by_priority(result)
    return result


def search_content(words, creator=None, orderby="hot_index"):
    # TODO 全文搜索排序使用索引
    assert isinstance(words, list)
    words = [word.lower() for word in words]

    def search_func(key, value):
        if value.content is None:
            return False
        return (value.creator == creator or value.is_public) \
            and textutil.contains_all(value.content.lower(), words)

    result = _full_db.list(filter_func=search_func,
                           offset=0, limit=MAX_SEARCH_SIZE)

    # 补全信息
    build_note_list_info(result)

    # 对笔记进行排序
    sort_notes(result, orderby)
    return result


def search_public(words):
    assert isinstance(words, list)
    words = [word.lower() for word in words]

    def search_public_func(key, value):
        if value.content is None:
            return False
        if not value.is_public:
            return False
        return textutil.contains_all(value.name.lower(), words)
    result = _full_db.list(filter_func=search_public_func,
                           offset=0, limit=MAX_SEARCH_SIZE)
    notes = [build_note_info(item) for item in result]
    sort_notes(notes)
    return notes


def check_and_remove_broken_notes(notes, user_name):
    result = []
    has_broken = False
    for note in notes:
        full = get_full_by_id(note.id)
        if full != None:
            result.append(note)
        else:
            logging.error("node=%s", note)
            NoteDao.delete_note(note.id)
            # 如果note_index被删除，delete_note也无法删除它，所以需要再删除一下
            db = get_note_tiny_table(note.creator)
            db.delete(note)
            has_broken = True
    return result


def count_removed(creator):
    def count_func(key, value):
        return value.is_deleted and value.creator == creator
    db = get_note_tiny_table(creator)
    return db.count(filter_func=count_func)


def list_removed(creator, offset, limit, orderby=None):
    def list_func(key, value):
        return value.is_deleted and value.creator == creator

    db = get_note_tiny_table(creator)
    notes = db.list(filter_func=list_func, offset=offset, limit=MAX_LIST_SIZE)
    notes = check_and_remove_broken_notes(notes, creator)
    sort_notes(notes, orderby)
    return notes[offset: offset + limit]


def document_filter_func(key, value):
    return value.type in ("md", "text", "html", "post", "log", "plan") and value.is_deleted == 0


def table_filter_func(key, value):
    return value.type in ("csv", "table") and value.is_deleted == 0


def get_filter_func(type, default_filter_func):
    if type == "document" or type == "doc":
        return document_filter_func
    if type in ("csv", "table"):
        return table_filter_func
    return default_filter_func


def list_by_type(creator, type, offset, limit, orderby="name", skip_archived=False):
    """按照类型查询笔记列表
    @param {str} creator 笔记作者
    @param {str|None} type  笔记类型
    @param {int} offset 下标
    @param {int} limit 返回的最大列数
    @param {str} orderby 排序
    @param {bool} skip_archived 是否跳过归档笔记
    """

    assert type != None, "note.dao.list_by_type: type is None"

    def list_func(key, value):
        if skip_archived and value.archived:
            return False
        if type != "all" and value.type != type:
            return False
        return value.is_deleted == 0

    filter_func = get_filter_func(type, list_func)

    db = get_note_tiny_table(creator)
    notes = db.list_by_index("ctime", filter_func=filter_func, offset=offset,
                             limit=limit, reverse=True)

    sort_notes(notes, orderby)
    return notes


def count_by_type(creator, type):
    def default_count_func(key, value):
        return value.type == type and value.creator == creator and value.is_deleted == 0
    filter_func = get_filter_func(type, default_count_func)
    return dbutil.prefix_count("note_tiny:%s" % creator, filter_func)


def list_sticky(creator, offset=0, limit=1000, orderby="ctime_desc"):
    def list_func(key, value):
        return value.priority > 0 and value.creator == creator and value.is_deleted == 0

    db = get_note_tiny_table(creator)

    notes = db.list(filter_func=list_func,
                    offset=offset, limit=MAX_STICKY_SIZE)
    sort_notes(notes, orderby=orderby)
    return notes[offset:offset+limit]


def count_sticky(creator):
    def list_func(key, value):
        return value.priority > 0 and value.creator == creator and value.is_deleted == 0
    db = get_note_tiny_table(creator)
    return db.count(filter_func=list_func)


def list_archived(creator, offset=0, limit=100):
    def list_func(key, value):
        return value.archived and value.creator == creator and value.is_deleted == 0
    notes = _tiny_db.list(
        user_name=creator, filter_func=list_func, offset=offset, limit=limit)
    sort_notes(notes)
    return notes


def list_by_func(creator, list_func, offset, limit):
    notes = _tiny_db.list(user_name=creator, filter_func=list_func,
                          offset=offset, limit=limit, reverse=True)
    build_note_list_info(notes)
    return notes

class SearchHistory(Storage):

    def __init__(self) -> None:
        self.user = ""
        self.key = ""
        self.category = "default"
        self.cost_time = 0.0
        self.ctime = dateutil.format_datetime()

def add_search_history(user, search_key: str, category="default", cost_time=0.0):
    if user == None:
        user = "public"
    
    if len(search_key) > MAX_SEARCH_KEY_LENGTH:
        return
    
    expire_search_history(user)
    
    value = SearchHistory()
    value.user = user
    value.key = search_key
    value.category = category
    value.cost_time = cost_time

    return _search_history_db.insert(value)


def list_search_history(user, limit=1000, orderby="time_desc"):
    if user is None or user == "":
        return []
    result = []
    for value in _search_history_db.list(limit = limit, reverse=True, where = dict(user=user)):
        if value.ctime == None:
            value.ctime = ""
        result.append(value)
    
    result.sort(key = lambda x:x.ctime, reverse = True)
    return result


def clear_search_history(user_name):
    assert user_name != None
    assert user_name != ""
    db = _search_history_db
    for item in db.list(where = dict(user=user_name), reverse=True, limit=1000):
        db.delete(item)

def expire_search_history(user_name, limit=1000):
    db = _search_history_db
    count = _search_history_db.count(where = dict(user = user_name))

    if count > limit:
        list_limit = min(20, count - limit)
        with dbutil.get_write_lock(user_name):
            for value in db.list(where = dict(user=user_name), limit = list_limit, reverse=False):
                db.delete(value)


class NoteStatDO(Storage):

    def __init__(self):
        self.total = 0
        self.group_count = 0
        self.doc_count = 0
        self.gallery_count = 0
        self.list_count = 0
        self.table_count = 0
        self.plan_count = 0
        self.log_count = 0
        self.sticky_count = 0
        self.removed_count = 0
        self.dict_count = 0
        self.comment_count = 0
        self.tag_count = 0
        self.update_time = 0.0

    def is_expired(self):
        expire_time = 60 * 60 # 1小时
        return time.time() - self.update_time > expire_time

    @classmethod
    def from_dict(cls, dict_value):
        result=NoteStatDO()
        result.update(dict_value)
        return result

@xutils.async_func_deco()
def refresh_note_stat_async(user_name):
    """异步刷新笔记统计"""
    refresh_note_stat(user_name)

@xutils.timeit_deco(name="NOTE_DAO:refresh_note_stat")
def refresh_note_stat(user_name):
    assert user_name != None, "[refresh_note_stat.assert] user_name != None"

    with dbutil.get_write_lock(user_name):
        stat = NoteStatDO()
        if user_name is None:
            return stat

        stat.total = count_by_creator(user_name)
        stat.group_count = count_group(user_name)
        stat.doc_count = count_by_type(user_name, "doc")
        stat.gallery_count = count_by_type(user_name, "gallery")
        stat.list_count = count_by_type(user_name, "list")
        stat.table_count = count_by_type(user_name, "table")
        stat.plan_count = count_by_type(user_name, "plan")
        stat.log_count = count_by_type(user_name, "log")
        stat.sticky_count = count_sticky(user_name)
        stat.removed_count = count_removed(user_name)
        stat.dict_count = count_dict(user_name)
        stat.comment_count = NoteDao.count_comment(user_name)
        stat.tag_count = NoteDao.count_tag(user_name)
        stat.update_time = time.time()

        dbutil.put("user_stat:%s:note" % user_name, stat)
        return stat

def get_empty_note_stat():
    stat = NoteStatDO()
    stat.total = 0
    stat.group_count = 0
    return stat


def get_note_stat(user_name):
    if user_name == None:
        return get_empty_note_stat()
    stat = dbutil.get("user_stat:%s:note" % user_name)
    if stat is None:
        stat = refresh_note_stat(user_name)
    else:
        stat = NoteStatDO.from_dict(stat)
        if stat.is_expired():
            stat = refresh_note_stat(user_name)
    if stat.tag_count == None:
        stat.tag_count = 0
    return stat


def get_gallery_path(note):
    import xconfig
    # 新的位置, 增加一级子目录（100个，二级子目录取决于文件系统
    # 最少的255个，最多无上限，也就是最少2.5万个相册，对于一个用户应该够用了）
    note_id = str(note.id)
    if len(note_id) < 2:
        second_dir = ("00" + note_id)[-2:]
    else:
        second_dir = note_id[-2:]
    standard_dir = os.path.join(
        xconfig.UPLOAD_DIR, note.creator, "gallery", second_dir, note_id)
    if os.path.exists(standard_dir):
        return standard_dir
    # TODO 归档的位置
    # 老的位置
    fpath = os.path.join(xconfig.UPLOAD_DIR, note.creator,
                         str(note.parent_id), note_id)
    if os.path.exists(fpath):
        # 修复数据另外通过工具实现
        return fpath

    # 如果依然不存在，创建一个地址
    fsutil.makedirs(standard_dir)
    return standard_dir


def get_virtual_group(user_name, name):
    if name == "ungrouped":
        files = list_by_parent(user_name, parent_id = "0", offset = 0, limit = 1000,
                               skip_group=True, include_public=False)
        group = NoteDO()
        group.name = "未分类笔记"
        group.url = "/note/default"
        group.size = len(files)
        group.children_count = len(files)
        group.icon = "fa-folder"
        group.priority = 1
        return group
    else:
        raise Exception("[get_virtual_group] invalid name: %s" % name)


def check_not_empty(value, method_name):
    if value == None or value == "":
        raise Exception("[%s] can not be empty" % method_name)


# write functions
xutils.register_func("note.create", create_note)
xutils.register_func("note.update", update_note)
xutils.register_func("note.update0", update0)
xutils.register_func("note.move", move_note)
xutils.register_func("note.visit",  visit_note)
xutils.register_func("note.touch",  touch_note)
xutils.register_func("note.create_token", create_token)

# 内部更新索引的接口，外部不要使用
xutils.register_func("note.update_index", update_index)
xutils.register_func("note.update_public_index", update_public_index)

# query functions
xutils.register_func("note.get_root", get_root)
xutils.register_func("note.get_default_group", get_default_group)
xutils.register_func("note.get_by_id", get_by_id)
xutils.register_func("note.get_by_token", get_by_token)
xutils.register_func("note.get_by_id_creator", get_by_id_creator)
xutils.register_func("note.get_by_name", get_by_name)
xutils.register_func("note.get_or_create", get_or_create_note)
xutils.register_func("note.get_virtual_group", get_virtual_group)
xutils.register_func("note.search_name", search_name)
xutils.register_func("note.search_content", search_content)
xutils.register_func("note.search_public", search_public)
xutils.register_func("note.batch_query_list", batch_query_list)

# list functions
xutils.register_func("note.list_path", list_path)
xutils.register_func("note.list_group", list_group)
xutils.register_func("note.list_default_notes", list_default_notes)
xutils.register_func("note.list_root_group", list_root_group)
xutils.register_func("note.list_by_parent", list_by_parent)
xutils.register_func("note.list_by_date", list_by_date)
xutils.register_func("note.list_by_type", list_by_type)
xutils.register_func("note.list_removed", list_removed)
xutils.register_func("note.list_sticky",  list_sticky)
xutils.register_func("note.list_archived", list_archived)
xutils.register_func("note.list_public", list_public)
xutils.register_func("note.list_by_func", list_by_func)

# count functions
xutils.register_func("note.count_public", count_public)
xutils.register_func("note.count_recent_edit", count_user_note)
xutils.register_func("note.count_user_note", count_user_note)
xutils.register_func("note.count_ungrouped", count_ungrouped)
xutils.register_func("note.count_removed", count_removed)
xutils.register_func("note.count_by_type", count_by_type)
xutils.register_func("note.count_by_parent",  count_by_parent)
xutils.register_func("note.count_group", count_group)

# others
xutils.register_func("note.find_prev_note", find_prev_note)
xutils.register_func("note.find_next_note", find_next_note)

# history
xutils.register_func("note.add_history", add_history)
xutils.register_func("note.list_history", list_history)
xutils.register_func("note.get_history", get_history)
xutils.register_func("note.add_search_history", add_search_history)
xutils.register_func("note.list_search_history", list_search_history)
xutils.register_func("note.clear_search_history", clear_search_history)
xutils.register_func("note.expire_search_history", expire_search_history)

# stat
xutils.register_func("note.get_note_stat", get_note_stat)
xutils.register_func("note.get_gallery_path", get_gallery_path)
xutils.register_func("note.refresh_note_stat_async", refresh_note_stat_async)

NoteDao.get_by_id_creator = get_by_id_creator
NoteDao.get_root = get_root
NoteDao.batch_query_list = batch_query_list
NoteDao.get_note_stat = get_note_stat
