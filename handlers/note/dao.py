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
search_history:<user>:<timeseq>  = 用户维度的搜索历史
note_public:<note_id>            = 公开的笔记索引
"""
import time
import os
import xconfig
import xutils
import xmanager
import logging
import xauth
from xutils import Storage
from xutils import dateutil, dbutil, textutil, fsutil

# 配置日志模块
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s|%(levelname)s|%(filename)s:%(lineno)d|%(message)s')


def register_note_table(name, description, check_user=False, user_attr=None):
    dbutil.register_table(name, description, "note",
                          check_user=check_user, user_attr=user_attr)


register_note_table("note_full", "笔记完整信息 <note_full:note_id>")
register_note_table("note_index", "笔记索引，不包含内容 <note_index:note_id>")
register_note_table("note_skey", "用户维度的skey索引 <note_skey:user:skey>")
register_note_table("notebook", "笔记分组", check_user=True, user_attr="creator")
register_note_table("token", "用于分享的令牌")
register_note_table("note_history", "笔记的历史版本")

dbutil.register_table("search_history", "搜索历史")

# 公开分享的笔记索引
register_note_table("note_public", "公共笔记索引")
dbutil.register_table_index("note_public", "hot_index")
dbutil.register_table_index("note_public", "share_time")

# 用户维度索引
register_note_table("note_tiny", "用户维度的笔记索引 <table:user:id>",
                    check_user=True, user_attr="creator")
dbutil.register_table_index("note_tiny", "name")
dbutil.register_table_index("note_tiny", "ctime")


NOTE_DAO = xutils.DAO("note")

_full_db = dbutil.get_table("note_full")
_tiny_db = dbutil.get_table("note_tiny")
_stat_db = dbutil.get_table("user_stat")
_index_db = dbutil.get_table("note_index")
_book_db = dbutil.get_table("notebook")

DB_PATH = xconfig.DB_PATH
MAX_EDIT_LOG = 500
MAX_VIEW_LOG = 500
MAX_STICKY_SIZE = 1000
MAX_SEARCH_SIZE = 1000
MAX_LIST_SIZE = 1000

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


class NoteSchema:
    """这个类主要是说明结构"""

    # 基本信息
    id = "主键ID"
    name = "笔记名称"
    ctime = "创建时间"
    mtime = "修改时间"
    atime = "访问时间"
    type = "类型"
    category = "所属分类"  # 一级图书分类
    size = "内容大小"
    children_count = "儿子节点数量"
    parent_id = "父级节点ID"
    content = "纯文本内容"
    data = "富文本内容"
    is_deleted = "是否删除"
    archived = "是否归档"

    # 权限控制
    creator = "创建者"
    is_public = "是否公开"
    token = "分享token"

    # 统计信息
    priority = "优先级"
    visited_cnt = "访问次数"
    orderby = "排序方式"
    hot_index = "热门指数"


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
    root = Storage()
    root.name = "根目录"
    root.type = "group"
    root.size = None
    root.id = "0"
    root.parent_id = "0"
    root.content = ""
    root.priority = 0
    root.creator = creator
    build_note_info(root)
    root.url = "/note/group"
    return root


def is_root_id(id):
    return id in (None, "", "0", 0)


def get_default_group():
    group = Storage()
    group.name = "默认分组"
    group.type = "group"
    group.size = None
    group.id = "default"
    group.parent_id = 0
    group.content = ""
    group.priority = 0
    build_note_info(group)
    group.url = "/note/default"
    return group


def get_archived_group():
    group = Storage()
    group.name = "归档分组"
    group.type = "group"
    group.size = None
    group.id = "archived"
    group.parent_id = 0
    group.content = ""
    group.priority = 0
    build_note_info(group)
    group.url = "/note/archived"
    return group


def get_note_public_table():
    return dbutil.get_table("note_public")


def get_note_tiny_table(user_name):
    return dbutil.get_table("note_tiny", user_name=user_name)


def batch_query(id_list):
    result = dict()
    for id in id_list:
        note = dbutil.get("note_index:%s" % id)
        if note:
            result[id] = note
            build_note_info(note)
    return result


def batch_query_list(id_list):
    result = []
    for id in id_list:
        note = dbutil.get("note_index:%s" % id)
        if note:
            build_note_info(note)
            result.append(note)
    return result


def sort_by_name(notes):
    notes.sort(key=lambda x: x.name)


def sort_by_name_desc(notes):
    notes.sort(key=lambda x: x.name, reverse=True)


def sort_by_name_priority(notes):
    sort_by_name(notes)
    sort_by_priority(notes)


def sort_by_mtime_desc(notes):
    notes.sort(key=lambda x: x.mtime, reverse=True)


def sort_by_ctime_desc(notes):
    notes.sort(key=lambda x: x.ctime, reverse=True)


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


SORT_FUNC_DICT = {
    "name": sort_by_name,
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
        note.orderby = "ctime_priority"

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

    if note.badge_info is None:
        note.badge_info = note.create_date

    if note.type == "group":
        _build_book_default_info(note)

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
    if str(id) == "0":
        return get_root(creator)

    note_index = dbutil.get("note_index:%s" % id)

    if not include_full and note_index != None:
        build_note_info(note_index)
        return note_index

    note = get_full_by_id(id)
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

    build_note_info(note)
    return note


def get_by_id_creator(id, creator, db=None):
    note = get_by_id(id, creator=creator)
    if note and note.creator == creator:
        return note
    return None


def get_by_token(token):
    token_info = dbutil.get("token:%s" % token)
    if token_info != None and token_info.type == "note":
        return get_by_id(token_info.id)
    return None


def get_by_user_skey(user_name, skey):
    skey = skey.replace("-", "_")
    note_info = dbutil.get("note_skey:%s:%s" % (user_name, skey))
    if note_info != None:
        return get_by_id(note_info.note_id)
    else:
        return None


def save_note_skey(note):
    skey = note.get("skey")
    if skey is None or skey == "":
        return
    key = "note_skey:%s:%s" % (note.creator, note.skey)
    dbutil.put(key, Storage(note_id=note.id))


def delete_note_skey(note):
    skey = note.skey
    if skey is None or skey == "":
        return
    key = "note_skey:%s:%s" % (note.creator, note.skey)
    dbutil.delete(key)


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
    note_dict["version"] = 0

    if note_id is not None:
        # 指定id创建笔记
        note_dict["id"] = note_id
        put_note_to_db(note_id, note_dict)
        # 创建日志
        add_create_log(note_dict)
        return note_id
    elif date_str is None or date_str == "":
        # 默认创建规则
        note_id = dbutil.timeseq()
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

        while True:
            note_id = "%020d" % timestamp
            note_dict["ctime"] = dateutil.format_datetime(timestamp/1000)
            old = get_by_id(note_id)
            if old is None:
                note_dict["id"] = note_id
                put_note_to_db(note_id, note_dict)

                # 创建日志
                add_create_log(note_dict)
                return note_id
            else:
                timestamp += 1


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

    with dbutil.get_write_lock():
        # 检查名称是否冲突
        if check_name:
            check_by_name(creator, name)

        # 创建笔记的基础信息
        note_id = create_note_base(note_dict, date_str, note_id)

    # 更新分组下面页面的数量
    update_children_count(note_dict["parent_id"])

    # 创建对应的文件夹
    if type == "gallery":
        dirname = os.path.join(xconfig.UPLOAD_DIR, creator, str(note_id))
        xutils.makedirs(dirname)

    # 更新统计数量
    refresh_note_stat_async(creator)

    # 更新目录修改时间
    touch_note(note_dict["parent_id"])

    # 保存skey索引
    save_note_skey(note_dict)

    # 最后发送创建笔记成功的消息
    create_msg = dict(name=name, type=type, id=note_id)
    xmanager.fire("note.add", create_msg)
    xmanager.fire("note.create", create_msg)

    return note_id


def create_token(type, id):
    uuid = textutil.generate_uuid()
    token_info = Storage(type=type, id=id)
    dbutil.put("token:%s" % uuid, token_info)
    return uuid


def add_create_log(note):
    NOTE_DAO.add_create_log(note.creator, note)


def add_visit_log(user_name, note):
    NOTE_DAO.add_visit_log(user_name, note)


def remove_virtual_fields(note):
    del_dict_key(note, "path")
    del_dict_key(note, "url")
    del_dict_key(note, "icon")
    del_dict_key(note, "show_edit")
    del_dict_key(note, "create_date")


def put_note_to_db(note_id, note):
    creator = note.creator

    # 删除不需要持久化的数据
    remove_virtual_fields(note)

    # 保存到DB
    _full_db.update_by_id(note_id, note)

    # 更新索引
    update_index(note)

    # 增加编辑日志
    NOTE_DAO.add_edit_log(creator, note)


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

    if note_id == "0":
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

    if "parent_id" in kw:
        raise Exception(
            "[note.dao.update_note] can not update `parent_id`, please use `note.dao.move_note`")

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
        return 0

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
    assert new_parent_id != None
    assert new_parent_id != 0
    assert new_parent_id != ""

    old_parent_id = note.parent_id
    note.parent_id = new_parent_id

    if old_parent_id == new_parent_id:
        return

    # 没有更新内容，只需要更新索引数据
    update_index(note)

    # 更新文件夹的容量
    update_children_count(old_parent_id)
    update_children_count(new_parent_id)

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

    def find_func(key, value):
        if value.is_deleted:
            return False
        return value.name == name
    db = get_note_tiny_table(creator)
    result = db.list(offset=0, limit=1, filter_func=find_func)
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

    update_index(note)
    add_visit_log(user_name, note)


def update_children_count(parent_id, db=None):
    if is_root_id(parent_id):
        return

    note = get_by_id(parent_id)
    if note is None:
        return

    creator = note.creator
    count = 0
    for child in list_by_parent(creator, parent_id):
        if child.type == "group":
            count += child.children_count or 0
        else:
            count += 1

    note.children_count = count
    update_index(note)


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
def list_group(creator=None,
               orderby="mtime_desc",
               skip_archived=False,
               status="all",
               *,
               offset=0, limit=1000,
               parent_id=None,
               category=None,
               tags=None,
               count_total=False,
               count_only=False):
    """查询笔记本列表"""
    assert creator != None
    check_group_status(status)

    if category == "" or category == "all":
        category = None
    
    q_tags = tags
    if tags != None and len(tags) == 0:
        q_tags = None

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

        if status == "archived":
            return value.archived

        if status == "active":
            return not value.archived
        
        return True

    if count_only:
        return _book_db.count(user_name=creator, filter_func=list_group_func)

    notes = _book_db.list(
        user_name=creator, filter_func=list_group_func, limit=1000)
    sort_notes(notes, orderby)
    result = notes[offset:offset + limit]
    
    if count_total:
        return result, _book_db.count(user_name = creator, filter_func=list_group_func)
    else:
        return result


def count_group(creator, status=None):
    check_group_status(status)

    if status is None:
        return _book_db.count(user_name=creator)

    return len(list_group(creator, status=status))


@xutils.timeit(name="NoteDao.ListRootGroup:leveldb", logfile=True)
def list_root_group(creator=None, orderby="name"):
    def list_root_group_func(key, value):
        return value.creator == creator and value.type == "group" and value.parent_id == 0 and value.is_deleted == 0

    notes = dbutil.prefix_list("notebook:%s" % creator, list_root_group_func)
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

    notes = dbutil.prefix_list("note_tiny:", list_default_func)
    sort_notes(notes, orderby)
    return notes[offset:offset+limit]


def list_public(offset, limit, orderby="ctime_desc"):
    if orderby == "hot":
        index_name = "hot_index"
    else:
        index_name = "share_time"

    db = dbutil.get_table("note_public")
    notes = db.list_by_index(index_name,
                             offset=offset, limit=limit, reverse=True)

    build_note_list_info(notes)
    for note in notes:
        if note.is_deleted:
            logging.warning("笔记已删除:%s,name:%s", note.id, note.name)
            db.delete_by_id(note.id)

    return notes


def count_public():
    db = get_note_public_table()
    return db.count()


@xutils.timeit(name="NoteDao.ListNote:leveldb", logfile=True, logargs=True)
def list_by_parent(creator, parent_id, offset=0, limit=1000,
                   orderby="name", skip_group=False, include_public=True):
    """通过父级节点ID查询笔记列表"""
    if parent_id is None:
        raise Exception("list_by_parent: parent_id is None")

    parent_id = str(parent_id)
    # TODO 添加索引优化

    def list_note_func(key, value):
        if value.is_deleted:
            return False
        if skip_group and value.type == "group":
            return False
        if str(value.parent_id) != parent_id:
            return False

        if include_public:
            return (value.is_public or value.creator == creator)
        else:
            return value.creator == creator

    notes = _tiny_db.list(offset=0, limit=limit, filter_func=list_note_func, user_name=creator)

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
    return count_ungrouped(creator, 0)


@xutils.timeit(name="NoteDao.CountNoteByParent", logfile=True, logargs=True, logret=True)
def count_by_parent(creator, parent_id):
    """统计笔记数量
    @param {string} creator 创建者
    @param {string/number} parent_id 父级节点ID
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


def add_history(id, version, note):
    if version is None:
        return
    note['note_id'] = id
    dbutil.put("note_history:%s:%s" % (id, version), note)


def list_history(note_id):
    history_list = dbutil.prefix_list("note_history:%s:" % note_id)
    history_list = sorted(
        history_list, key=lambda x: x.mtime or "", reverse=True)
    return history_list


def delete_history(note_id, version=None):
    pass


def get_history(note_id, version):
    # note = table.select_first(where = dict(note_id = note_id, version = version))
    return dbutil.get("note_history:%s:%s" % (note_id, version))


def search_name(words, creator=None, parent_id=None, orderby="hot_index"):
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
            delete_note(note.id)
            # 如果note_index被删除，delete_note也无法删除它，所以需要再删除一下
            db = get_note_tiny_table(note.creator)
            db.delete(note)
            has_broken = True

    if has_broken:
        refresh_note_stat(user_name)
    return result


def count_removed(creator):
    def count_func(key, value):
        return value.is_deleted and value.creator == creator
    return dbutil.prefix_count("note_tiny:%s" % creator, count_func)


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


def add_search_history(user, search_key, category="default", cost_time=0):
    key = "search_history:%s:%s" % (user, dbutil.timeseq())
    dbutil.put(key, Storage(key=search_key,
               category=category, cost_time=cost_time))


def list_search_history(user, limit=1000, orderby="time_desc"):
    if user is None or user == "":
        return []
    return dbutil.prefix_list("search_history:%s" % user, reverse=True, limit=limit)


def clear_search_history(user_name):
    assert user_name != None
    assert user_name != ""
    db = dbutil.get_list_table("search_history", user_name=user_name)
    for item in db.iter(reverse=True, limit=-1):
        db.delete(item)


@xutils.async_func_deco()
def refresh_note_stat_async(user_name):
    """异步刷新笔记统计"""
    with dbutil.get_write_lock():
        refresh_note_stat(user_name)


def refresh_note_stat(user_name):
    assert user_name != None, "[refresh_note_stat.assert] user_name != None"

    stat = Storage()

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
    stat.comment_count = NOTE_DAO.count_comment(user_name)

    dbutil.put("user_stat:%s:note" % user_name, stat)
    return stat


def get_note_stat(user_name):
    stat = dbutil.get("user_stat:%s:note" % user_name)
    if stat is None:
        stat = refresh_note_stat(user_name)
    return stat


def get_gallery_path(note):
    import xconfig
    # 新的位置, 增加一级子目录（100个，二级子目录取决于文件系统，最少的255个，最多无上限，也就是最少2.5万个相册，对于一个用户应该够用了）
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
        files = list_by_parent(user_name, 0, 0, 1000,
                               skip_group=True, include_public=False)
        group = Storage()
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

# stat
xutils.register_func("note.get_note_stat", get_note_stat)
xutils.register_func("note.get_gallery_path", get_gallery_path)
xutils.register_func("note.refresh_note_stat_async", refresh_note_stat_async)
