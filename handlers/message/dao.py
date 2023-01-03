# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/06/12 22:59:33
# @modified 2022/04/11 23:29:47
import xutils
import xconfig
import xmanager
import re
from xutils import dbutil, cacheutil, textutil, Storage, functions
from xutils import dateutil
from xutils.functions import del_dict_key
from xtemplate import T

dbutil.register_table("message", "短文本", check_user=True, user_attr="user")
dbutil.register_table_index("message", "date")
dbutil.register_table_index("message", "tag")

dbutil.register_table("msg_search_history", "备忘搜索历史",
                      check_user=True, user_attr="user")

dbutil.register_table("msg_key", "备忘关键字/标签")
dbutil.register_table("msg_task_idx", "待办索引")
dbutil.register_table("msg_history", "备忘历史")

VALID_MESSAGE_PREFIX_TUPLE = ("message:", "msg_key:", "msg_task:")
# 带日期创建的最大重试次数
CREATE_MAX_RETRY = 20
MOBILE_LENGTH = 11
VALID_TAG_SET = set(["task", "done", "log", "key", "date"])

_keyword_db = dbutil.get_hash_table("msg_key")
_msg_db = dbutil.get_table("message")
_msg_stat_cache = cacheutil.PrefixedCache("msgStat:")


class MessageDO(Storage):

    id = "主键"
    tag = "标签"
    user = "用户名"

    def __init__(self):
        pass


def check_before_create(kw):
    if "id" in kw:
        raise Exception("message.dao.create: can not set id")
    if "user" not in kw:
        raise Exception("message.dao.create: key `user` is missing")

    if 'tag' not in kw:
        raise Exception("message.dao.create: key `tag` is missing")

    if "ctime" not in kw:
        raise Exception("message.dao.create: key `ctime` is missing")

    if "content" not in kw:
        raise Exception("message.dao.create: key `content` is missing")

    tag = kw["tag"]
    if tag not in VALID_TAG_SET:
        raise Exception("message.dao.create: tag `%s` is invalid" % tag)


def convert_to_task_idx_key(key):
    assert isinstance(key, str)
    prefix, user_name, timeseq = key.split(":")
    return "msg_task_idx:%s:%s" % (user_name, timeseq)


def convert_to_task_index(kw):
    index = Storage()
    index.tag = kw["tag"]
    index.user = kw["user"]
    index.content = kw["content"]
    return index


def build_task_index(kw):
    tag = kw["tag"]

    if tag == "task" or tag == "done" or tag == "todo":
        task_key = convert_to_task_idx_key(kw["id"])
        task_index = convert_to_task_index(kw)
        dbutil.put(task_key, task_index)


def execute_after_create(kw):
    build_task_index(kw)


def execute_after_update(kw):
    build_task_index(kw)


def execute_after_delete(kw):
    build_task_index(kw)


def get_message_key(user_name, timestamp):
    assert user_name != None
    assert timestamp != None
    return "message:%s:%s" % (user_name, dbutil.timeseq(timestamp))


def _create_message_with_date(kw):
    user_name = kw["user"]
    date = kw["date"]
    old_ctime = kw["ctime"]
    kw["tag"] = "log"

    today = dateutil.get_today()

    if today == date:
        return _create_message_without_date(kw)

    timestamp = dateutil.parse_date_to_timestamp(date)
    timestamp += 60 * 60 * 23  # 追加日志的开始时间默认为23点

    kw["ctime0"] = old_ctime
    kw["date"] = date
    # 调整类型为记事
    retry = 0

    while True:
        with dbutil.get_write_lock():
            if retry > CREATE_MAX_RETRY:
                raise Exception("message.dao.create: too many retry")

            key = get_message_key(user_name, timestamp)
            kw["ctime"] = dateutil.format_time(timestamp)
            kw["id"] = key
            result = _msg_db.get_by_key(key)
            if result is None:
                _msg_db.update_by_key(key, kw)
                execute_after_create(kw)
                return key
            else:
                timestamp += 1

            retry += 1


def _create_message_without_date(kw):
    tag = kw['tag']
    ctime = kw["ctime"]
    kw['date'] = dateutil.format_date(ctime)

    if tag == 'key':
        key = "msg_key:%s:%s" % (kw['user'], dbutil.timeseq())
        kw["id"] = key
        dbutil.put(key, kw)
    else:
        _msg_db.insert(kw)
        key = kw["_key"]
        kw["id"] = key
        _msg_db.update(kw)

    execute_after_create(kw)
    return key


def create_message(**kw):
    """创建信息
    @param {string} user 用户名
    @param {string} tag 类型
    @param {string} ctime 创建时间
    @param {string|None} date 日期，可选的
    @param {string} content 文本的内容
    """
    check_before_create(kw)
    kw["version"] = 0
    tag = kw['tag']

    if tag == "date":
        return _create_message_with_date(kw)
    else:
        return _create_message_without_date(kw)


def check_before_update(message):
    id = message['id']
    if not id.startswith(VALID_MESSAGE_PREFIX_TUPLE):
        raise Exception("[msg.update] invalid message id:%s" % id)


def fix_before_update(message):
    if message.tag is None:
        # 修复tag为空的情况，这种一般是之前的待办任务，只有状态没有tag
        if message.status == 100:
            message.tag = "done"
        else:
            message.tag = "task"

    del_dict_key(message, "html")
    del_dict_key(message, "tag_text")


def update_message(message):
    check_before_update(message)
    fix_before_update(message)
    id = message["id"]
    if id.startswith("message:"):
        _msg_db.update(message)
    else:
        dbutil.put(id, message)
    execute_after_update(message)


def add_message_history(message):
    id_str = message['id']
    prefix, user, timeseq = id_str.split(':')
    new_id = 'msg_history:%s:%s:%s' % (
        user, timeseq, message.get('version', 0))
    dbutil.put(new_id, message)


@xmanager.listen(["message.update", "message.add", "message.remove"])
def expire_message_cache(ctx):
    cacheutil.prefix_del("message.count")


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
    @param {string} user_name 用户名
    @param {string} key 要搜索的关键字
    @param {int} offset 下标
    @param {int} limit 返回结果最大限制
    @param {list} search_tags 搜索的标签集合
    @param {bool} no_tag 是否搜索无标签的
    @param {bool} count_only 只统计数量
    @param {string} date 日期过滤条件
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

    if id.startswith("message:"):
        _msg_db.delete(old)
    else:
        dbutil.delete(id)

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


def get_message_by_id(full_key):
    # type: (str) -> object
    check_param_id(full_key)
    if full_key.startswith("message:"):
        value = _msg_db.get_by_key(full_key)
        if value != None:
            value["id"] = full_key
        return value
    else:
        return dbutil.get(full_key)


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


def list_file_page(user, offset, limit):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("file://") >= 0
    chatlist = _msg_db.list(filter_func=filter_func, offset=offset,
                            limit=limit, reverse=True, user_name=user)
    # TODO 后续可以用message_stat加速
    amount = _msg_db.count(filter_func=filter_func, user_name=user)
    return chatlist, amount


def list_link_page(user, offset, limit):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("http://") >= 0 or value.content.find("https://") >= 0
    chatlist = dbutil.prefix_list(
        "message:%s" % user, filter_func, offset, limit, reverse=True)
    # TODO 后续可以用message_stat加速
    amount = dbutil.prefix_count("message:%s" % user, filter_func)
    return chatlist, amount


def list_book_page(user, offset, limit, key=None):
    pattern = re.compile(r"《.+》")

    def filter_func(key, value):
        if value.content is None:
            return False
        return pattern.search(value.content)

    msg_list = dbutil.prefix_list(
        "message:%s" % user, filter_func, offset, limit, reverse=True)
    # TODO 后续可以用message_stat加速
    amount = dbutil.prefix_count("message:%s" % user, filter_func)
    return msg_list, amount


def list_people_page(user, offset, limit, key=None):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("@") >= 0

    msg_list = dbutil.prefix_list(
        "message:%s" % user, filter_func, offset, limit, reverse=True)
    # TODO 后续可以用message_stat加速
    amount = dbutil.prefix_count("message:%s" % user, filter_func)
    return msg_list, amount


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

    msg_list = dbutil.prefix_list(
        "message:%s" % user, filter_func, offset, limit, reverse=True)
    # TODO 后续可以用message_stat加速
    amount = dbutil.prefix_count("message:%s" % user, filter_func)
    return msg_list, amount


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


def list_key(user, offset, limit=-1):
    items = dbutil.prefix_list("msg_key:%s" % user)
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
        filter_func = get_content_filter_func(None, content)
        msg_list = dbutil.prefix_list("msg_key:%s" % user, filter_func, 0, 1)
        return functions.first_or_none(msg_list)
    else:
        return None


def list_task(user, offset=0, limit=xconfig.PAGE_SIZE):
    return list_by_tag(user, "task", offset, limit)


def list_task_done(user, offset=0, limit=xconfig.PAGE_SIZE):
    return list_by_tag(user, "done", offset, limit)


def list_by_tag(user, tag, offset=0, limit=xconfig.PAGE_SIZE):
    check_param_user(user)

    if tag == "key":
        chatlist = list_key(user, offset, limit)
    else:
        filter_func = get_filter_by_tag_func(tag)
        if tag == "task":
            chatlist = _msg_db.list_by_index(
                "tag", index_value=tag, filter_func=filter_func, 
                offset=offset, limit=limit, reverse=True, user_name=user)
        else:
            chatlist = _msg_db.list(
                filter_func=filter_func, offset=offset, limit=limit, reverse=True, user_name=user)

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

    def list_by_date_func(key, value):
        return value.ctime.find(date) == 0

    amount = dbutil.prefix_count("message:%s" % user, list_by_date_func)

    msg_list = dbutil.prefix_list(
        "message:%s" % user, list_by_date_func, offset, limit, reverse=True)

    return msg_list, amount


def count_by_tag(user, tag):
    """内部方法"""
    if tag == "key":
        return dbutil.count_table("msg_key:%s" % user)
    if tag == "all":
        return dbutil.count_table("message:%s" % user)
    return dbutil.prefix_count("message:%s" % user, get_filter_by_tag_func(tag))


def get_message_stat0(user):
    stat = dbutil.get("user_stat:%s:message" % user)
    if stat != None:
        if stat.canceled_count is None:
            stat.canceled_count = 0
    return stat


def get_empty_stat():
    stat = Storage()
    stat.task_count = 0
    stat.log_count = 0
    stat.done_count = 0
    stat.cron_count = 0
    stat.key_count = 0
    stat.canceled_count = 0
    return stat

def get_message_stat(user):
    if user == None:
        return get_empty_stat()
    check_param_user(user)

    value = _msg_stat_cache.get(user)
    print("[get_message_stat] cacheValue=", value)

    if value == None:
        value = get_message_stat0(user)
        _msg_stat_cache.put(user, value)

    if value is None:
        return refresh_message_stat(user)

    return value


def refresh_message_stat(user):
    if user == None:
        return
    # TODO 优化，只需要更新原来的tag和新的tag
    task_count = count_by_tag(user, "task")
    log_count = count_by_tag(user, "log")
    done_count = count_by_tag(user, "done")
    cron_count = count_by_tag(user, "cron")
    key_count = count_by_tag(user, "key")
    canceled_count = count_by_tag(user, "canceled")
    stat = get_message_stat0(user)
    if stat is None:
        stat = Storage()

    stat.task_count = task_count
    stat.log_count = log_count
    stat.done_count = done_count
    stat.cron_count = cron_count
    stat.key_count = key_count
    stat.canceled_count = canceled_count
    dbutil.put("user_stat:%s:message" % user, stat)

    _msg_stat_cache.delete(user)

    return stat


def add_search_history(user, search_key, cost_time=0):
    key = "msg_search_history:%s:%s" % (user, dbutil.timeseq())
    dbutil.put(key, Storage(key=search_key, cost_time=cost_time))


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

class MessageDao:
    """message的数据接口"""

    @staticmethod
    def get_by_id(full_key):
        return get_message_by_id(full_key)
    
    @staticmethod
    def create(**kw):
        return create_message(**kw)
    
    @staticmethod
    def update(message):
        return update_message(message)

    @staticmethod
    def delete(full_key):
        return delete_message_by_id(full_key)

    @staticmethod
    def add_search_history(user, search_key, cost_time=0):
        return add_search_history(user, search_key, cost_time)

    @staticmethod
    def add_history(message):
        return add_message_history(message)
    
    @staticmethod
    def refresh_message_stat(user):
        return refresh_message_stat(user)
    
    @staticmethod
    def get_message_stat(user):
        return get_message_stat(user)

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
