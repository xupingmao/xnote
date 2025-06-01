# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/06/12 22:59:33
# @modified 2022/04/11 23:29:47
import xutils
import re
import logging
import typing
from xnote.core import xconfig, xmanager, xtables, xauth

from xutils import dbutil, cacheutil, textutil, Storage, functions
from xutils import dateutil
from xnote.core.xtemplate import T
from xnote.service.search_service import SearchHistoryDO, SearchHistoryType, SearchHistoryService
from xutils.db.dbutil_helper import new_from_dict
from xnote.service import MsgTagBindService as _MsgTagBindService
from xnote.service import TagTypeEnum
from .message_model import is_task_tag
from .message_model import MessageDO
from .message_model import MsgIndex
from .message_model import VALID_MESSAGE_PREFIX_TUPLE
from .message_model import MessageHistory
from .message_model import MessageStatItem
from .message_model import MOBILE_LENGTH
from .message_model import MsgTagInfo
from .message_model import MessageTagEnum, MessageSecondTypeEnum
from xnote.service import TagInfoDO


_msg_db = dbutil.get_table("msg_v2")
_msg_stat_cache = cacheutil.PrefixedCache("msgStat:")
_msg_history_db = dbutil.get_table_v2("msg_history")

_debug = False

def build_task_index(kw):
    pass

def execute_after_create(kw):
    build_task_index(kw)


def execute_after_update(kw):
    build_task_index(kw)


def execute_after_delete(kw):
    build_task_index(kw)

def _create_message_with_date(kw):
    assert isinstance(kw, MessageDO)
    date = kw.date
    today = dateutil.get_today()

    if today == date or date == "":
        return _create_message_without_date(kw)

    timestamp = dateutil.parse_date_to_timestamp(date)
    timestamp += 60 * 60 * 23 + 60 * 59 # 追加日志的开始时间默认为23点59
    ctime = dateutil.format_datetime(timestamp)
    change_time = ctime

    kw.ctime0 = xutils.format_datetime()
    kw.ctime = ctime
    kw.date = date
    kw.change_time = change_time

    msg_index = MsgIndex()
    msg_index.tag = kw.tag
    msg_index.user_name = kw.user
    msg_index.user_id = xauth.UserDao.get_id_by_name(kw.user)
    msg_index.ctime_sys = xutils.format_datetime()
    msg_index.ctime = ctime
    msg_index.date = date
    msg_index.change_time = change_time
    msg_id = MsgIndexDao.insert(msg_index)
    _msg_db.update_by_id(str(msg_id), kw)
    kw.id = kw._key
    return kw._key


def _create_message_without_date(kw):
    assert isinstance(kw, MessageDO)

    tag = kw.tag
    ctime = kw.ctime
    kw.date = dateutil.format_date(ctime)

    index = MsgIndex()
    index.tag = tag
    index.ctime = ctime
    index.date = kw.date
    index.user_name = kw.user
    index.user_id = xauth.UserDao.get_id_by_name(kw.user)
    index.change_time = ctime

    msg_id = MsgIndexDao.insert(index)
    _msg_db.update_by_id(str(msg_id), kw)
    
    kw.id = kw._key
    execute_after_create(kw)
    return kw._key


def create_message(message: MessageDO):
    # type: (MessageDO) -> str
    """创建信息
    :param {str} user: 用户名
    :param {str} tag: 类型
    :param {str} ctime: 创建时间
    :param {str|None} date: 日期，可选的
    :param {str} content: 文本的内容
    """
    assert isinstance(message, MessageDO)
    message.check_before_create()
    message.fix_before_save()
    return _create_message_with_date(message)


def update_message(message: MessageDO):
    assert isinstance(message, MessageDO)
    message.check_before_update()
    message.fix_before_save()
    _msg_db.update(message)
    MsgIndexDao.touch(int(message._id))
    execute_after_update(message)


def add_message_history(message: MessageDO):
    assert isinstance(message, MessageDO)
    history_obj = MessageHistory()
    history_obj.msg_id = message.get_int_id()
    history_obj.msg_version = message.get("version", 0)
    history_obj.content = message.content
    history_obj.user_id = message.user_id
    
    _msg_history_db.insert(history_obj.__dict__)


def get_words_from_key(key):
    words = []
    for item in key.split():
        if item == "":
            continue
        words.append(item.lower())
    return words


def has_tag_fast(content):
    return content.find("#") >= 0 or content.find("@") >= 0

def is_user_tag(key=""):
    return key.startswith("#") and key.endswith("#") and key.count("#") == 2

def search_message(user_id: int, key: str, offset=0, limit=20, *, search_tags=None, no_tag=None, count_only=False, date=""):
    """搜索短信
    :param {int} user_id: 用户名
    :param {str} key: 要搜索的关键字
    :param {int} offset: 下标
    :param {int} limit: 返回结果最大限制
    :param {list} search_tags: 搜索的标签集合
    :param {bool} no_tag: 是否搜索无标签的
    :param {bool} count_only: 只统计数量
    :param {str} date: 日期过滤条件
    """
    assert date != None
    assert key != None

    if is_user_tag(key) and date == "":
        second_type = 0
        if search_tags != None:
            assert len(search_tags) == 1
            second_type = MessageStatItem.get_second_type_by_code(search_tags[0])
        return search_message_by_user_tag(user_id=user_id, key=key, offset=offset, limit=limit, second_type=second_type)
    
    words = get_words_from_key(key)

    def search_func_default(key, value):
        if value.content is None:
            return False
        if no_tag is True and has_tag_fast(value.content):
            return False
        value_date = dateutil.format_date(value.ctime)
        if value_date == None or not value_date.startswith(date):
            return False
        return textutil.contains_all(value.content.lower(), words)

    def search_func_with_tags(key, value):
        if value.tag not in search_tags:
            return False
        return search_func_default(key, value)

    if search_tags != None:
        search_func = search_func_with_tags
    else:
        search_func = search_func_default

    if count_only:
        chatlist = []
    else:
        chatlist = _msg_db.list(filter_func=search_func, offset=offset,
                                limit=limit, reverse=True, user_name=str(user_id))
        # 按照创建时间倒排 (按日期补充的随手记的key不是按时间顺序的)
    
    chatlist = MessageDO.from_dict_list(chatlist)
    chatlist.sort(key = lambda x:x.change_time, reverse=True)
    amount = _msg_db.count(filter_func=search_func, user_name=str(user_id))
    return chatlist, amount


def search_message_by_user_tag(user_id=0, key="", offset=0, limit=20, second_type=0):
    bindlist = MsgTagBindDao.list_by_key(user_id=user_id, key=key, offset=offset, limit=limit, second_type=second_type)
    count = MsgTagBindDao.count_by_key(user_id=user_id, key=key, second_type=second_type)
    msg_ids = []
    for item in bindlist:
        msg_ids.append(item.target_id)
    return MessageDao.batch_get_by_ids(user_id, msg_ids), count


def check_before_delete(id):
    if not id.startswith(VALID_MESSAGE_PREFIX_TUPLE):
        raise Exception("[delete] invalid message id:%s" % id)


def delete_message_by_id(id):
    # type: (str) -> None
    check_before_delete(id)

    old = get_message_by_id(id)

    if old == None:
        return
    index_id = int(old._id)
    _msg_db.delete(old)
    MsgIndexDao.delete_by_id(index_id)


    xmanager.fire("message.remove", Storage(id=id))
    execute_after_delete(old)


@xutils.timeit(name="Kv.Message.Count", logfile=True)
def kv_count_message(user: str, status):
    user_id = xauth.UserDao.get_id_by_name(user)
    def filter_func(k, v):
        return v.status == status
    return _msg_db.count(filter_func=filter_func, user_name=str(user_id))


@xutils.cache(prefix="message.count.status", expire=60)
def count_message(user, status):
    return kv_count_message(user, status)

def get_message_by_key(full_key, user_name=""):
    if full_key == None:
        return None
    if not full_key.startswith(_msg_db.prefix):
        return None
    value = _msg_db.get_by_key(full_key)
    if value != None:
        value = MessageDO.from_dict(value)
        value.id = full_key
        if user_name != "" and user_name != value.user:
            return None
    return value

get_message_by_id = get_message_by_key

def check_param_user(user_name):
    if user_name is None or user_name == "":
        raise Exception("[query] invalid user_name:%s" % user_name)


def check_param_id(id):
    if id is None:
        raise Exception("param id is None")
    if not id.startswith(VALID_MESSAGE_PREFIX_TUPLE):
        raise Exception("param id invalid: %s" % id)


@xutils.timeit(name="kv.message.list", logfile=True, logargs=True)
def list_message_page(user: str, status, offset, limit):
    def filter_func(key, value):
        if status is None:
            return value.user == user
        value.id = key
        return value.user == user and value.status == status
    user_id = xauth.UserDao.get_id_by_name(user)
    chatlist0 = _msg_db.list(filter_func=filter_func, offset=offset,
                            limit=limit, reverse=True, user_name=str(user_id))
    chatlist = MessageDO.from_dict_list(chatlist0)
    amount = _msg_db.count(filter_func=filter_func, user_name=str(user_id))
    return chatlist, amount

def query_special_page(user_name="", filter_func=None, offset=0, limit=10):
    user_id = xauth.UserDao.get_id_by_name(user_name)
    chatlist0 = _msg_db.list(filter_func=filter_func, offset=offset,
                            limit=limit, reverse=True, user_name=str(user_id))
    chatlist = MessageDO.from_dict_list(chatlist0)
    chatlist.sort(key = lambda x:x.ctime, reverse=True)
    # TODO 后续可以用message_stat加速
    amount = _msg_db.count(filter_func=filter_func, user_name=str(user_id))
    return chatlist, amount

def filter_todo_func(key, value):
    # 兼容老版本的数据
    return value.tag in ("task", "cron", "todo") or value.status == 0 or value.status == 50


def get_filter_by_tag_func(tag):
    if tag in ("task", "todo"):
        return filter_todo_func

    def filter_func(key, value):
        if tag is None or tag == "all":
            return True
        if tag == "done":
            return value.tag == "done" or value.status == 100
        return value.tag == tag
    return filter_func


def list_key(user, offset=0, limit=1000):
    user_id = xauth.UserDao.get_id_by_name(user)
    items = MsgIndexDao.list(user_id=user_id, tag="key", offset=offset, limit=limit)
    items.sort(key=lambda x: x.mtime, reverse=True)

    if limit < 0:
        return items[offset:]

    return items[offset: offset+limit]


def get_content_filter_func(tag, content):
    def filter_func(key, value):
        if tag is None:
            return value.content == content
        return value.tag == tag and value.content == content
    return filter_func


def get_by_content(user, tag, content, user_id=0):
    if tag == "key":
        if user_id == 0:
            user_id = xauth.UserDao.get_id_by_name(user)
        # tag是独立的表，不需要比较tag
        value = MsgTagInfoDao.get_first(user_id=user_id, content=content)
        return MsgTagInfo.from_dict_or_None(value)
    else:
        return None

def list_task(user, offset=0, limit=xconfig.PAGE_SIZE):
    return list_by_tag(user, "task", offset, limit)


def list_task_done(user, offset=0, limit=xconfig.PAGE_SIZE):
    return list_by_tag(user, "done", offset, limit)

def list_by_system_tag(user_id:int, tag_code: str, offset=0, limit=xconfig.PAGE_SIZE):
    second_type = MessageSecondTypeEnum.log.int_value
    return search_message_by_user_tag(user_id=user_id, key=tag_code, 
                                      offset=offset, limit=limit, second_type=second_type)

def list_by_tag(user: str, tag: str, offset=0, limit=xconfig.PAGE_SIZE):
    check_param_user(user)

    if tag == "key":
        raise Exception("tag=key not supported")
    else:
        user_id = xauth.UserDao.get_id_by_name(user)
        index_list = MsgIndexDao.list(user_id=user_id, tag=tag, offset=offset, limit=limit)
        chatlist = MessageDao.batch_get_by_index_list(index_list, user_id=user_id)

    if MessageTagEnum.is_system_tag_code(tag):
        # 系统标签处理
        return list_by_system_tag(user_id, tag, offset, limit)

    # 利用message_stat优化count查询
    if tag == "done":
        amount = get_message_stat(user).done_count
    elif tag == "task" or tag == "todo":
        amount = get_message_stat(user).task_count
    elif tag == "cron":
        amount = get_message_stat(user).cron_count
    elif tag == "log":
        amount = get_message_stat(user).log_count
    else:
        amount = count_by_tag(user, tag)

    if amount is None:
        amount = 0
    return chatlist, amount


def list_by_date(user, date, offset=0, limit=xconfig.PAGE_SIZE, tag=""):
    if date is None or date == "":
        return []
    
    user_id = xauth.UserDao.get_id_by_name(user)
    index_list = MsgIndexDao.list(user_id=user_id,tag=tag, date_prefix=date, offset=offset, limit=limit)
    msg_list = MessageDao.batch_get_by_index_list(index_list, user_id=user_id)
    amount = MsgIndexDao.count(user_id=user_id, date_prefix=date)
    return msg_list, amount

def list_by_date_range(user_id=0, tag="", date_start="", date_end="", offset=0, limit=1000):
    user_info = xauth.UserDao.get_by_id(user_id)
    assert user_info != None
    user_name = user_info.name
    index_list = MsgIndexDao.list(user_id=user_id, tag=tag, date_start=date_start, date_end=date_end, offset=offset, limit=limit)
    msg_list = MessageDao.batch_get_by_index_list(index_list=index_list, user_id=user_id)
    amount = MsgIndexDao.count(user_id=user_id, tag=tag, date_start=date_start, date_end=date_end)
    return msg_list, amount

def count_by_tag(user:str, tag):
    """内部方法"""
    if tag == "key":
        return MsgTagInfoDao.count(user=user)
    
    if tag == "all":
        user_id = xauth.UserDao.get_id_by_name(user)
        return MsgIndexDao.count(user_id=user_id)
    
    if tag in ("task", "done", "log"):
        user_id = xauth.UserDao.get_id_by_name(user)
        return MsgIndexDao.count(user_id=user_id, tag=tag)
    
    user_id = xauth.UserDao.get_id_by_name(user)
    return _msg_db.count_by_func(user_name=str(user_id), filter_func=get_filter_by_tag_func(tag))
    # return dbutil.prefix_count(f"message:{user_id}", get_filter_by_tag_func(tag))


def get_message_stat0(user=""):
    stat = dbutil.get("user_stat:%s:message" % user)
    result = MessageStatDO()
    if stat != None:
        assert isinstance(stat, Storage)
        result.update(stat)
    return result


class MessageStatDO(xutils.Storage):
    def __init__(self, **kw):
        self.task_count = 0
        self.log_count = 0
        self.done_count = 0
        self.cron_count = 0
        self.key_count = 0
        self.canceled_count = 0
        self.update(kw)

def get_empty_stat():
    return MessageStatDO()

def get_message_stat(user):
    # type: (str) -> MessageStatDO
    """读取随手记的状态"""
    if user == None:
        return get_empty_stat()
    check_param_user(user)

    value = _msg_stat_cache.get_dict(user)

    if _debug:
        logging.debug("[get_message_stat] cacheValue=%s", value)

    if value == None:
        value = get_message_stat0(user)
        _msg_stat_cache.put(user, value)

    if value is None:
        return refresh_message_stat(user)

    return MessageStatDO(**value)


def refresh_message_stat(user, tag_list=[]) -> MessageStatDO:
    if user == None:
        return get_empty_stat()

    stat = get_message_stat0(user)
    if stat is None:
        stat = get_empty_stat()

    update_all = len(tag_list) == 0
    if update_all or "task" in tag_list:
        task_count = count_by_tag(user, "task")
        stat.task_count = task_count
    if update_all or "log" in tag_list:
        log_count = count_by_tag(user, "log")
        stat.log_count = log_count
    if update_all or "done" in tag_list:
        done_count = count_by_tag(user, "done")
        stat.done_count = done_count
    if update_all or "cron" in tag_list:
        cron_count = count_by_tag(user, "cron")
        stat.cron_count = cron_count
    if update_all or "key" in tag_list:
        key_count = count_by_tag(user, "key")
        stat.key_count = key_count
    if update_all or "canceled" in tag_list:
        canceled_count = count_by_tag(user, "canceled")
        stat.canceled_count = canceled_count

    dbutil.put("user_stat:%s:message" % user, stat)
    _msg_stat_cache.delete(user)

    return stat

class MessageStatDao:

    db = dbutil.get_table("user_stat")

    @classmethod
    def put_by_user(cls, user="", stat={}):
        cls.db.put_by_id(f"{user}:message", stat)

class MsgSearchLogDao:

    max_log_size = xconfig.DatabaseConfig.user_max_log_size
    
    @classmethod
    def add_log(cls, user_name="", search_key="", cost_time=0):
        user_id = xauth.UserDao.get_id_by_name(user_name)
        search_type = SearchHistoryType.msg

        search_history = SearchHistoryDO()
        search_history.user_id = user_id
        search_history.ctime = dateutil.format_datetime()
        search_history.search_key = search_key
        search_history.search_type = search_type
        search_history.cost_time_ms = cost_time

        if SearchHistoryService.count(user_id=user_id, search_type=search_type) > cls.max_log_size:
            ids = []
            for item in SearchHistoryService.list(user_id=user_id, search_type=search_type, limit=20, order="ctime asc"):
                ids.append(item.id)
            SearchHistoryService.delete_by_ids(ids)


def add_search_history(user="", search_key="", cost_time=0):
    MsgSearchLogDao.add_log(user_name=user, search_key=search_key, cost_time=cost_time)


def get_message_stat_item(user, tag, priority=0):
    msg_stat = get_message_stat(user)

    if tag == "log":
        return MessageStatItem(tag, msg_stat.log_count, priority=priority)
    if tag == "task":
        return MessageStatItem(tag, msg_stat.task_count, priority=priority)

    raise Exception("unknown tag:%s" % tag)

class MsgIndexDao:
    """随手记索引表,使用SQL存储"""
    db = xtables.get_table_by_name("msg_index")

    @classmethod
    def insert(cls, msg_index: MsgIndex):
        msg_index.pop("id")
        assert msg_index.tag != ""
        assert msg_index.ctime != ""
        assert msg_index.ctime_sys != ""
        assert msg_index.date != ""
        assert msg_index.user_id != 0
        assert msg_index.user_name != ""

        if msg_index.change_time == xtables.DEFAULT_DATETIME:
            msg_index.change_time = msg_index.ctime

        msg_index.mtime = dateutil.format_datetime()
        return cls.db.insert(**msg_index)
    
    @classmethod
    def count(cls, user_id=0, tag = "", date_prefix="", date_start="", date_end=""):
        where = "1=1"
        if user_id != 0:
            where += " AND user_id=$user_id"
        
        if tag != "":
            where += " AND tag=$tag"
        
        if date_prefix != "":
            where += " AND date LIKE $date_prefix"
        if date_start != "":
            where += " AND date >= $date_start"
        if date_end != "":
            where += " AND date < $date_end"

        vars = dict(user_id=user_id, tag=tag, date_prefix=date_prefix+"%", date_start=date_start, date_end=date_end)
        return cls.db.count(where=where, vars=vars)
    
    @classmethod
    def list(cls, user_id=0, tag="", date_prefix="", date_start="", date_end="", offset=0, limit=10, order="change_time desc"):
        where = "1=1"
        if user_id != 0:
            where += " AND user_id=$user_id"
        if tag != "":
            where += " AND tag=$tag"
        if date_prefix != "":
            where += " AND date LIKE $date_prefix"
        if date_start != "":
            where += " AND date >= $date_start"
        if date_end != "":
            where += " AND date < $date_end"

        vars = dict(user_id=user_id, tag=tag, date_prefix=date_prefix+"%", date_start=date_start, date_end=date_end)
        result = cls.db.select(where=where, vars=vars,offset=offset,limit=limit,order=order)
        return MsgIndex.from_dict_list(result)
    
    @classmethod
    def delete_by_id(cls, id=0):
        return cls.db.delete(where=dict(id=id))
    
    @classmethod
    def get_by_id(cls, id=0):
        if id == 0:
            return None
        result = cls.db.select_first(where=dict(id=id))
        if result == None:
            return None
        return MsgIndex(**result)
    
    @classmethod
    def update_tag(cls, id=0, tag="", update_time=xtables.DEFAULT_DATETIME):
        updates = dict()
        updates["tag"] = tag
        updates["mtime"] = update_time
        updates["change_time"] = update_time
        return cls.db.update(where=dict(id=id), **updates)
    
    @classmethod
    def touch(cls, id=0):
        now = xutils.format_datetime()
        return cls.db.update(mtime=now, where=dict(id=id))
    
    @classmethod
    def get_first(cls, user_id=0, content="", tag=""):
        where = "1=1"
        if user_id != 0:
            where += " AND user_id=$user_id"
        if tag != "":
            where += " AND tag=$tag"
        vars = dict(user_id=user_id, tag=tag)
        return cls.db.select_first(where=where, vars=vars)

    @classmethod
    def iter_batch(cls, user_id=0, batch_size=20):
        where = ""
        if user_id != 0:
            where = "user_id=$user_id"
        for batch in cls.db.iter_batch(batch_size=batch_size, where=where, vars=dict(user_id=user_id)):
            yield MsgIndex.from_dict_list(batch)

    @classmethod
    def iter_all(cls):
        for item in cls.db.iter():
            yield MsgIndex.from_dict(item)

class MsgTagInfoDao:
    """随手记标签元信息表,使用KV存储"""
    db = xtables.get_table_by_name("tag_info")
    tag_type = TagTypeEnum.msg_tag.int_value

    @classmethod
    def get_first(cls, user_id=0, content="", user_name=""):
        if user_id == 0:
            user_id = xauth.UserDao.get_id_by_name(user_name)
        where_dict = dict(user_id=user_id, tag_code=content, tag_type=cls.tag_type)
        result = cls.db.select_first(where=where_dict)
        return MsgTagInfo.from_dict_or_None(result)
    
    @classmethod
    def get_by_id(cls, user_id=0, tag_id=0):
        where_dict = dict(user_id=user_id, tag_id=tag_id)
        result = cls.db.select_first(where=where_dict)
        return MsgTagInfo.from_dict_or_None(result)
    
    @classmethod
    def list(cls, user="", user_id=0, offset=0, limit=20, tag_code="", order=""):
        if user_id == 0:
            user_id = xauth.UserDao.get_id_by_name(user)
        records, _ = cls.get_page(user_id=user_id, offset=offset, limit=limit, tag_code=tag_code, order=order, skip_count=True)
        return records
    
    @classmethod
    def get_page(cls, user_id=0, offset=0, limit=20, tag_code="", order="", skip_count=False):
        where_dict = {}
        where_dict["user_id"] = user_id
        where_dict["tag_type"] = cls.tag_type
        if tag_code != "" and tag_code != None:
            where_dict["tag_code"] = tag_code
        order = cls.format_order(order)
        records = cls.db.select(where=where_dict, offset=offset,limit=limit,order=order)
        
        if skip_count:
            amount = 0
        else:
            amount = cls.db.count(where=where_dict)
        
        return MsgTagInfo.from_dict_list(records), amount

    @classmethod
    def format_order(cls, orderby=""):
        if orderby == "amount_desc":
            return "amount desc"
        if orderby == "visit":
            return "visit_cnt desc"
        if orderby == "recent":
            return "mtime desc"
        if orderby == "":
            return "mtime desc"
        return orderby

    @classmethod
    def update(cls, tag_info: MsgTagInfo):
        tag_info.mtime = xutils.format_datetime()
        tag_id = tag_info.tag_id
        update_dict = tag_info.to_save_dict()
        return cls.db.update(where=dict(tag_id=tag_id), **update_dict)

    @classmethod
    def delete_by_id(cls, tag_id=0):
        return cls.db.delete(where=dict(tag_id=tag_id))
    
    @classmethod
    def delete(cls, obj: TagInfoDO):
        return cls.delete_by_id(obj.tag_id)

    @classmethod
    def get_or_create(cls, user_id=0, content=""):
        item = cls.get_first(user_id=user_id, content=content)
        if item != None:
            return MsgTagInfo.from_dict(item)
        else:
            now = dateutil.format_datetime()
            record = MsgTagInfo()
            record.tag_type = TagTypeEnum.msg_tag.int_value
            record.ctime = now
            record.mtime = now
            record.user_id = user_id
            record.tag_code = content
            new_id = cls.db.insert(**record.to_save_dict())
            record.tag_id = int(new_id)
            return record

    @classmethod
    def count(cls, user=""):
        user_id = xauth.UserDao.get_id_by_name(user)
        return cls.db.count(where=dict(user_id=user_id))

class MsgTagBindDao:

    tag_bind_service = _MsgTagBindService

    @classmethod
    def bind_tags(cls, user_id=0, msg_id=0, tags=[], second_type=0, sort_value=""):
        if user_id == 0:
            logging.error("user_id=0")
            return
        cls.tag_bind_service.bind_tags(user_id=user_id, target_id=msg_id, tags=tags, update_only_changed=True, second_type=second_type, sort_value=sort_value)

    @classmethod
    def update_second_type(cls, user_id=0, msg_id=0, second_type=0, sort_value=""):
        cls.tag_bind_service.update_second_type(user_id=user_id, target_id=msg_id, second_type=second_type, sort_value=sort_value)
        
    @classmethod
    def count_by_key(cls, user_id=0, key="", second_type=0):
        assert isinstance(user_id, int)
        assert isinstance(key, str)
        return cls.tag_bind_service.count_user_tag(user_id=user_id, tag_code=key, second_type=second_type)
    
    @classmethod
    def list_by_key(cls, user_id=0, key="", second_type=0, offset=0, limit=20):
        return cls.tag_bind_service.list_by_tag(user_id=user_id, tag_code=key, second_type=second_type, offset=offset, limit=limit) 

class MessageDao:
    """message的主数据接口,使用KV存储"""

    @staticmethod
    def get_by_id(full_key):
        return get_message_by_key(full_key)
    
    @staticmethod
    def get_by_key(full_key):
        return get_message_by_key(full_key)
    
    @staticmethod
    def batch_get_by_ids(user_id=0, ids=[]):
        key_list = []
        for item in ids:
            key_list.append(_msg_db._build_key(str(user_id), str(item)))
        return MessageDao.batch_get_by_keys(key_list)
        
    @staticmethod
    def batch_get_by_keys(key_list=[]):
        result_dict = _msg_db.batch_get_by_key(key_list=key_list)
        records = []
        for row_id in key_list:
            result_item = result_dict.get(row_id)
            if result_item != None:
                records.append(result_item)
        return MessageDO.from_dict_list(records)
    
    @staticmethod
    def create(message):
        return create_message(message)
    
    @staticmethod
    def update(message):
        return update_message(message)
    
    @staticmethod
    def update_user_tags(message:MessageDO):
        msg_id = message.get_int_id()
        sort_value = str(message.change_time)
        tags = set(message.full_keywords).union(set(message.system_tags))
        MsgTagBindDao.bind_tags(message.user_id, msg_id=msg_id, tags=tags, 
                                second_type=message.get_second_type(), sort_value=sort_value)
    
    @classmethod
    def update_tag(cls, message:MessageDO, tag=""):
        now = dateutil.format_datetime()
        message.tag = tag
        message.change_time = now
        MsgIndexDao.update_tag(id=int(message._id), tag=tag, update_time=now)
        second_type = message.get_second_type()
        MsgTagBindDao.update_second_type(user_id=message.user_id, msg_id=message.get_int_id(), 
                                         second_type=second_type, sort_value=now)
        cls.update(message)
        cls.refresh_message_stat(message.user)

    @staticmethod
    def delete(full_key):
        return delete_message_by_id(full_key)
    
    @staticmethod
    def delete_by_key(full_key):
        return delete_message_by_id(full_key)

    @staticmethod
    def add_search_history(user, search_key, cost_time=0):
        return add_search_history(user, search_key, cost_time)

    @staticmethod
    def add_history(message):
        return add_message_history(message)
    
    @staticmethod
    def refresh_message_stat(user, tag_list=[]):       
        return refresh_message_stat(user, tag_list)
    
    @staticmethod
    def get_message_stat(user):
        return get_message_stat(user)
    
    @staticmethod
    def get_message_stat_item(user, tag, priority=0):
        return get_message_stat_item(user, tag, priority)
    
    @classmethod
    def batch_get_by_index_list(cls, index_list: typing.List[MsgIndex], user_id=0) -> typing.List[MessageDO]:
        id_list = []
        for index in index_list:
            id_list.append(str(index.id))

        dict_result = _msg_db.batch_get_by_id(id_list, user_name=str(user_id))
        result = []
        for index in index_list:
            msg = dict_result.get(str(index.id))
            if msg != None:
                new_msg = MessageDO.from_dict(msg)
                new_msg.change_time = index.change_time
                result.append(new_msg)
        return result
    
    @classmethod
    def iter_all(cls):
        for index_batch in MsgIndexDao.iter_batch():
            keys = []
            for index in index_batch:
                keys.append(_msg_db._build_key(str(index.user_id), str(index.id)))
            
            yield from cls.batch_get_by_keys(keys)

xutils.register_func("message.create", create_message)
xutils.register_func("message.update", update_message)
xutils.register_func("message.search", search_message)
xutils.register_func("message.delete", delete_message_by_id)
xutils.register_func("message.count", count_message)

xutils.register_func("message.find_by_id", get_message_by_id)
xutils.register_func("message.get_by_id",  get_message_by_id)
xutils.register_func("message.get_by_content", get_by_content)
xutils.register_func("message.get_message_tag", get_message_stat_item)

xutils.register_func("message.list", list_message_page)
xutils.register_func("message.list_task", list_task)
xutils.register_func("message.list_task_done", list_task_done)
xutils.register_func("message.list_by_tag",  list_by_tag)
xutils.register_func("message.list_by_date", list_by_date)

xutils.register_func("message.get_message_stat", get_message_stat)
xutils.register_func("message.refresh_message_stat", refresh_message_stat)
xutils.register_func("message.add_search_history", add_search_history)
xutils.register_func("message.add_history", add_message_history)
