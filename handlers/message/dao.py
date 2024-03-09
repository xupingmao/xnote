# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/06/12 22:59:33
# @modified 2022/04/11 23:29:47
import xutils
import re
import logging
import copy
from xnote.core import xconfig, xmanager, xtables, xauth

from xutils import dbutil, cacheutil, textutil, Storage, functions
from xutils import dateutil
from xutils.functions import del_dict_key
from xnote.core.xtemplate import T
from xutils.db.dbutil_helper import new_from_dict
from xnote.service import TagBindService, TagTypeEnum
from .message_model import is_task_tag
from xutils import numutil

VALID_MESSAGE_PREFIX_TUPLE = ("message:", "msg_key:", "msg_task:")
# 带日期创建的最大重试次数
CREATE_MAX_RETRY = 20
MOBILE_LENGTH = 11
VALID_TAG_SET = set(["task", "done", "log", "key"])

_msg_db = dbutil.get_table("message")
_msg_stat_cache = cacheutil.PrefixedCache("msgStat:")
_msg_history_db = dbutil.get_table_v2("msg_history")

_debug = False

sys_comment_dict = {
    "$mark_task_done$": T("标记任务完成"),
    "$reopen_task$": T("重新开启任务"),
}

class MessageHistory:
    def __init__(self):
        self.msg_id = 0
        self.msg_version = 0
        self.user_id = 0
        self.content = ""
        self.ctime = dateutil.format_datetime()

class MessageDO(Storage):
    def __init__(self):
        self._key = "" # kv的主键
        self._id = "" # kv的ID

        self.id = "" # 主键
        self.tag = "" # tag标签 {task, done, log, key}
        self.user = "" # 用户名
        self.user_id = 0 # 用户ID
        self.ip = ""
        self.ref = None # 引用的id
        self.ctime = xutils.format_datetime()  # 展示的创建时间
        self.ctime0 = xutils.format_datetime() # 实际的创建时间
        self.mtime = xutils.format_datetime()
        self.date = xutils.format_date()
        self.content = ""
        self.comments = [] # 评论信息
        self.version = 0
        self.visit_cnt = 0
        self.status = None # 老的结构
        self.keywords = None
        self.full_keywords = set()
        self.no_tag = True
        self.amount = 0 # keyword对象的数量
        self.done_time = None # type: str|None
        self.sort_value = ""

    @classmethod
    def from_dict(cls, dict_value: dict):
        result = MessageDO()
        result.update(dict_value)
        result.id = result._key
        if result.comments == None:
            result.comments = []
        for item in result.comments:
            comment_text = item.get("content")
            item["content"] = sys_comment_dict.get(comment_text, comment_text)
        if result.sort_value == "":
            index = MsgIndexDao.get_by_id(numutil.parse_int(result._id))
            if index != None:
                result.sort_value = index.sort_value
                MessageDao.update(result)
            
        return result
    
    @classmethod
    def from_dict_list(cls, dict_list):
        result = []
        for item in dict_list:
            result.append(cls.from_dict(item))
        return result
    
    @classmethod
    def from_dict_or_None(cls, dict_value):
        if dict_value == None:
            return None
        return cls.from_dict(dict_value)

    def check_before_update(self):
        id = self.id
        if not id.startswith(VALID_MESSAGE_PREFIX_TUPLE):
            raise Exception("[msg.update] invalid message id:%s" % id)

    def fix_before_update(self):
        if self.tag is None:
            # 修复tag为空的情况，这种一般是之前的待办任务，只有状态没有tag
            if self.status == 100:
                self.tag = "done"
            if self.status in (0, 50):
                self.tag = "task"

        del_dict_key(self, "html")
        del_dict_key(self, "tag_text")
        del_dict_key(self, "full_keywords")
        
        if self.status == None:
            self.pop("status", None)
        if self.amount == None:
            self.pop("amount", None)
        if self.ref == None:
            self.pop("ref", None)
        if self.keywords == None:
            self.pop("keywords", None)

    def check_before_create(self):
        if self.id != "":
            raise Exception("message.dao.create: can not set id")
        
        if self.user == "":
            raise Exception("message.dao.create: key `user` is missing")

        if self.ctime == "":
            raise Exception("message.dao.create: key `ctime` is missing")

        if self.tag != "done" and self.content == "":
            raise Exception("message.dao.create: key `content` is missing")

        if self.tag not in VALID_TAG_SET:
            raise Exception("message.dao.create: tag `%s` is invalid" % self.tag)
        
    def append_comment(self, comment_text=""):
        comment = MessageComment()
        comment.content = comment_text
        self.comments.append(comment)

    def get_int_id(self):
        return int(self._id)


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

    kw.ctime0 = xutils.format_datetime()
    kw.ctime = ctime
    kw.date = date

    msg_index = MsgIndex()
    msg_index.tag = kw.tag
    msg_index.user_name = kw.user
    msg_index.user_id = xauth.UserDao.get_id_by_name(kw.user)
    msg_index.ctime_sys = xutils.format_datetime()
    msg_index.ctime = ctime
    msg_index.date = date
    msg_index.sort_value = ctime
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
    index.sort_value = ctime

    msg_id = MsgIndexDao.insert(index)
    _msg_db.update_by_id(str(msg_id), kw)
    
    kw.id = kw._key
    execute_after_create(kw)
    return kw._key


def create_message(message):
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
    message.fix_before_update()
    return _create_message_with_date(message)


def update_message(message):
    assert isinstance(message, MessageDO)
    message.check_before_update()
    message.fix_before_update()
    _msg_db.update(message)
    MsgIndexDao.touch(int(message._id))
    execute_after_update(message)


def add_message_history(message):
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


def search_message(user_name, key, offset=0, limit=20, *, search_tags=None, no_tag=None, count_only=False, date=""):
    """搜索短信
    :param {str} user_name: 用户名
    :param {str} key: 要搜索的关键字
    :param {int} offset: 下标
    :param {int} limit: 返回结果最大限制
    :param {list} search_tags: 搜索的标签集合
    :param {bool} no_tag: 是否搜索无标签的
    :param {bool} count_only: 只统计数量
    :param {str} date: 日期过滤条件
    """
    assert user_name != None and user_name != ""
    assert date != None

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
                                limit=limit, reverse=True, user_name=user_name)
        # 按照创建时间倒排 (按日期补充的随手记的key不是按时间顺序的)
    
    chatlist = MessageDO.from_dict_list(chatlist)
    chatlist.sort(key = lambda x:x.sort_value, reverse=True)
    amount = _msg_db.count(filter_func=search_func, user_name=user_name)
    return chatlist, amount


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
def kv_count_message(user, status):
    def filter_func(k, v):
        return v.status == status
    return _msg_db.count(filter_func=filter_func, user_name=user)


@xutils.cache(prefix="message.count.status", expire=60)
def count_message(user, status):
    return kv_count_message(user, status)

def get_message_by_id(full_key, user_name=""):
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

def check_param_user(user_name):
    if user_name is None or user_name == "":
        raise Exception("[query] invalid user_name:%s" % user_name)


def check_param_id(id):
    if id is None:
        raise Exception("param id is None")
    if not id.startswith(VALID_MESSAGE_PREFIX_TUPLE):
        raise Exception("param id invalid: %s" % id)


@xutils.timeit(name="kv.message.list", logfile=True, logargs=True)
def list_message_page(user, status, offset, limit):
    def filter_func(key, value):
        if status is None:
            return value.user == user
        value.id = key
        return value.user == user and value.status == status
    chatlist = _msg_db.list(filter_func=filter_func, offset=offset,
                            limit=limit, reverse=True, user_name=user)

    amount = _msg_db.count(filter_func=filter_func, user_name=user)
    return chatlist, amount

def query_special_page(user_name="", filter_func=None, offset=0, limit=10):
    chatlist = _msg_db.list(filter_func=filter_func, offset=offset,
                            limit=limit, reverse=True, user_name=user_name)
    chatlist.sort(key = lambda x:x.ctime, reverse=True)
    # TODO 后续可以用message_stat加速
    amount = _msg_db.count(filter_func=filter_func, user_name=user_name)
    return chatlist, amount

def list_file_page(user, offset, limit):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("file://") >= 0
    return query_special_page(user_name=user, offset=offset, limit=limit, filter_func=filter_func)


def list_link_page(user, offset, limit):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("http://") >= 0 or value.content.find("https://") >= 0
    return query_special_page(user_name=user, offset=offset, limit=limit, filter_func=filter_func)


def list_book_page(user, offset, limit, key=None):
    pattern = re.compile(r"《.+》")

    def filter_func(key, value):
        if value.content is None:
            return False
        return pattern.search(value.content)
    
    return query_special_page(user_name=user, offset=offset, limit=limit, filter_func=filter_func)


def list_people_page(user, offset, limit, key=None):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("@") >= 0

    return query_special_page(user_name=user, offset=offset, limit=limit, filter_func=filter_func)


def list_phone_page(user, offset, limit, key=None):
    pattern = re.compile(r"([0-9]+)")

    def filter_func(key, value):
        if value.content is None:
            return False
        result = pattern.findall(value.content)
        for item in result:
            if len(item) == MOBILE_LENGTH:
                return True
        return False

    return query_special_page(user_name=user, offset=offset, limit=limit, filter_func=filter_func)


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


def get_by_content(user, tag, content):
    if tag == "key":
        # tag是独立的表，不需要比较tag
        value = MsgTagInfoDao.get_first(user=user, content=content)
        return MsgTagInfo.from_dict_or_None(value)
    else:
        return None

def delete_keyword(user, content):
    first = MsgTagInfoDao.get_first(user=user, content=content)
    if first != None:
        MsgTagInfoDao.delete(first)

def list_task(user, offset=0, limit=xconfig.PAGE_SIZE):
    return list_by_tag(user, "task", offset, limit)


def list_task_done(user, offset=0, limit=xconfig.PAGE_SIZE):
    return list_by_tag(user, "done", offset, limit)


def list_by_tag(user, tag, offset=0, limit=xconfig.PAGE_SIZE):
    check_param_user(user)

    if tag == "key":
        chatlist = MsgTagInfoDao.list(user=user, offset=offset, limit=limit)
    else:
        user_id = xauth.UserDao.get_id_by_name(user)
        index_list = MsgIndexDao.list(user_id=user_id, tag=tag, offset=offset, limit=limit)
        
        chatlist = MessageDao.batch_get_by_index_list(index_list, user_name=user)

    # 利用message_stat优化count查询
    if tag == "done":
        amount = get_message_stat(user).done_count
    elif tag == "task" or tag == "todo":
        amount = get_message_stat(user).task_count
    elif tag == "cron":
        amount = get_message_stat(user).cron_count
    elif tag == "log":
        amount = get_message_stat(user).log_count
    elif tag == "key":
        amount = get_message_stat(user).key_count
    else:
        amount = count_by_tag(user, tag)

    if amount is None:
        amount = 0
    return chatlist, amount


def list_by_date(user, date, offset=0, limit=xconfig.PAGE_SIZE):
    if date is None or date == "":
        return []
    
    user_id = xauth.UserDao.get_id_by_name(user)
    index_list = MsgIndexDao.list(user_id=user_id, date_prefix=date, offset=offset, limit=limit)
    msg_list = MessageDao.batch_get_by_index_list(index_list, user_name=user)
    amount = MsgIndexDao.count(user_id=user_id, date_prefix=date)
    return msg_list, amount

def list_by_date_range(user_id=0, tag="", date_start="", date_end="", offset=0, limit=1000):
    user_info = xauth.UserDao.get_by_id(user_id)
    assert user_info != None
    user_name = user_info.name
    index_list = MsgIndexDao.list(user_id=user_id, tag=tag, date_start=date_start, date_end=date_end, offset=offset, limit=limit)
    msg_list = MessageDao.batch_get_by_index_list(index_list=index_list, user_name=user_name)
    amount = MsgIndexDao.count(user_id=user_id, tag=tag, date_start=date_start, date_end=date_end)
    return msg_list, amount

def count_by_tag(user, tag):
    """内部方法"""
    if tag == "key":
        return MsgTagInfoDao.count(user=user)
    
    if tag == "all":
        user_id = xauth.UserDao.get_id_by_name(user)
        return MsgIndexDao.count(user_id=user_id)
    
    if tag in ("task", "done", "log"):
        user_id = xauth.UserDao.get_id_by_name(user)
        return MsgIndexDao.count(user_id=user_id, tag=tag)
    
    return dbutil.prefix_count("message:%s" % user, get_filter_by_tag_func(tag))


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
    def get_table(cls, user_name=""):
        return dbutil.get_hash_table("msg_search_history", user_name=user_name)

    @classmethod
    def add_log(cls, user_name="", search_key="", cost_time=0):
        user_db = cls.get_table(user_name)
        search_log = Storage(key=search_key, cost_time=cost_time)
        user_db.put(dbutil.timeseq(), search_log)

        if user_db.count() > cls.max_log_size:
            keys = []
            for key, value in user_db.list(limit=20):
                keys.append(key)
            user_db.batch_delete(keys=keys)


def add_search_history(user="", search_key="", cost_time=0):
    MsgSearchLogDao.add_log(user_name=user, search_key=search_key, cost_time=cost_time)


class MessageTag(Storage):

    def __init__(self, tag, size, priority=0):
        self.type = type
        self.size = size
        self.url = "/message?tag=" + tag
        self.priority = priority
        self.show_next = True
        self.is_deleted = 0
        self.name = "Message"
        self.icon = "fa-file-text-o"
        self.category = None
        self.badge_info = size

        if tag == "log":
            self.name = T("随手记")
            self.icon = "fa-file-text-o"

        if tag == "task":
            self.name = T("待办任务")
            self.icon = "fa-calendar-check-o"


def get_message_tag(user, tag, priority=0):
    msg_stat = get_message_stat(user)

    if tag == "log":
        return MessageTag(tag, msg_stat.log_count, priority=priority)
    if tag == "task":
        return MessageTag(tag, msg_stat.task_count, priority=priority)

    raise Exception("unknown tag:%s" % tag)

class MessageComment(Storage):
    def __init__(self):
        self.time = dateutil.format_datetime()
        self.content = ""

class MsgIndex(Storage):
    def __init__(self, **kw):
        self.id = 0
        self.tag = ""
        self.user_id = 0
        self.user_name = ""
        self.ctime_sys = dateutil.format_datetime() # 实际创建时间
        self.ctime = dateutil.format_datetime() # 展示创建时间
        self.mtime = dateutil.format_datetime() # 修改时间
        self.date = "1970-01-01"
        self.sort_value = "" # 排序字段, 对于log/task,存储创建时间,对于done,存储完成时间
        self.update(kw)

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
    def list(cls, user_id=0, tag="", date_prefix="", date_start="", date_end="", offset=0, limit=10, order="sort_value desc"):
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
        return cls.db.select(where=where, vars=vars,offset=offset,limit=limit,order=order)
    
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
    def update_tag(cls, id=0, tag="", sort_value=""):
        now = xutils.format_datetime()
        updates = dict()
        updates["tag"] = tag
        updates["mtime"] = now
        if sort_value != "":
            updates["sort_value"] = sort_value
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
        yield from cls.db.iter_batch(batch_size=batch_size, where="user_id=$user_id", vars=dict(user_id=user_id))

class MsgTagInfo(Storage):
    def __init__(self):
        self._key = "" # kv的真实key
        self.id = ""
        self.ctime = xutils.format_datetime()
        self.mtime = xutils.format_datetime()
        self.user = ""
        self.content=""
        self.amount=0
        self.is_marked=False
        self.visit_cnt=0
    
    @staticmethod
    def from_dict(dict_value):
        result = new_from_dict(MsgTagInfo, dict_value)
        result.id = result._key
        return result
    
    @classmethod
    def from_dict_or_None(cls, dict_value):
        if dict_value == None:
            return None
        return cls.from_dict(dict_value)

class MsgTagInfoDao:
    """随手记标签元信息表,使用KV存储"""
    db = dbutil.get_table("msg_key")

    @classmethod
    def get_first(cls, user="", content=""):
        where = dict(user=user, content=content)
        return cls.db.get_first(where=where)
    
    @classmethod
    def get_by_key(cls, key=""):
        result = cls.db.get_by_key(key)
        return MsgTagInfo.from_dict_or_None(result)
    
    @classmethod
    def list(cls, user="", offset=0, limit=20, content=None):
        where = {}
        if content != None:
            where["content"] = content
        return cls.db.list(where=where, user_name=user,offset=offset,limit=limit,reverse=True)
    
    @classmethod
    def update(cls, tag_info: MsgTagInfo):
        tag_info.mtime = xutils.format_datetime()
        return cls.db.update(tag_info)

    @classmethod
    def delete_by_id(cls, id=""):
        return cls.db.delete_by_id(id=id)
    
    @classmethod
    def delete(cls, obj):
        return cls.db.delete(obj)

    @classmethod
    def get_or_create(cls, user="", content=""):
        item = cls.get_first(user=user, content=content)
        if item != None:
            return MsgTagInfo.from_dict(item)
        else:
            record = MsgTagInfo()
            record.user = user
            record.content = content
            cls.db.insert(record)
            record.id = record._key
            return record

    @classmethod
    def count(cls, user=""):
        return cls.db.count(user_name=user)

class MsgTagBindDao:

    tag_bind_service = TagBindService(TagTypeEnum.msg_tag)

    @classmethod
    def bind_tags(cls, user_id=0, msg_id=0, tags=[]):
        if user_id == 0:
            logging.error("user_id=0")
            return
        cls.tag_bind_service.bind_tags(user_id=user_id, target_id=msg_id, tags=tags, update_only_changed=True)
        
    @classmethod
    def count_by_key(cls, user_id=0, key=""):
        assert isinstance(user_id, int)
        assert isinstance(key, str)
        return cls.tag_bind_service.count_user_tag(user_id=user_id, tag_code=key)

class MessageDao:
    """message的主数据接口,使用KV存储"""

    @staticmethod
    def get_by_id(full_key):
        return get_message_by_id(full_key)
    
    @staticmethod
    def create(message):
        return create_message(message)
    
    @staticmethod
    def update(message):
        return update_message(message)
    
    @staticmethod
    def update_user_tags(message:MessageDO):
        msg_id = message.get_int_id()
        MsgTagBindDao.bind_tags(message.user_id, msg_id=msg_id, tags=message.full_keywords)
    
    @classmethod
    def update_tag(cls, message:MessageDO, tag="", sort_value=""):
        message.tag = tag
        MsgIndexDao.update_tag(id=int(message._id), tag=tag, sort_value=sort_value)
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
    def get_message_tag(user, tag, priority=0):
        return get_message_tag(user, tag, priority)
    
    @classmethod
    def batch_get_by_index_list(cls, index_list, user_name=""):
        id_list = []
        for index in index_list:
            id_list.append(str(index.id))

        dict_result = _msg_db.batch_get_by_id(id_list, user_name=user_name)
        result = []
        for index in index_list:
            msg = dict_result.get(str(index.id))
            if msg != None:
                new_msg = MessageDO.from_dict(msg)
                new_msg.sort_value = index.sort_value
                result.append(new_msg)
        return result

xutils.register_func("message.create", create_message)
xutils.register_func("message.update", update_message)
xutils.register_func("message.search", search_message)
xutils.register_func("message.delete", delete_message_by_id)
xutils.register_func("message.count", count_message)

xutils.register_func("message.find_by_id", get_message_by_id)
xutils.register_func("message.get_by_id",  get_message_by_id)
xutils.register_func("message.get_by_content", get_by_content)
xutils.register_func("message.get_message_tag", get_message_tag)

xutils.register_func("message.list", list_message_page)
xutils.register_func("message.list_file", list_file_page)
xutils.register_func("message.list_link", list_link_page)
xutils.register_func("message.list_book", list_book_page)
xutils.register_func("message.list_people", list_people_page)
xutils.register_func("message.list_phone", list_phone_page)
xutils.register_func("message.list_task", list_task)
xutils.register_func("message.list_task_done", list_task_done)
xutils.register_func("message.list_by_tag",  list_by_tag)
xutils.register_func("message.list_by_date", list_by_date)

xutils.register_func("message.get_message_stat", get_message_stat)
xutils.register_func("message.refresh_message_stat", refresh_message_stat)
xutils.register_func("message.add_search_history", add_search_history)
xutils.register_func("message.add_history", add_message_history)
