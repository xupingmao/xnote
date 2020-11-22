# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/06/12 22:59:33
# @modified 2020/11/22 13:19:21
import xutils
import xconfig
import xmanager
import xtables
from xutils import dbutil, cacheutil, textutil, Storage, functions
from xtemplate import T


dbutil.register_table("message", "短文本")
dbutil.register_table("msg_search_history", "备忘搜索历史")
dbutil.register_table("msg_key", "备忘搜索关键字")
dbutil.register_table("msg_history", "备忘历史")
dbutil.register_table("user_stat", "用户数据统计")

class MessageDO(Storage):

    id   = "主键"
    tag  = "标签"
    user = "用户名"

    def __init__(self):
        pass

def create_message(**kw):
    tag = kw['tag']
    if tag == 'key':
        key = "msg_key:%s:%s" % (kw['user'], dbutil.timeseq())
    else:
        key = "message:%s:%s" % (kw['user'], dbutil.timeseq())
    kw['id'] = key
    dbutil.put(key, kw)
    return key

def update_message(message):
    id = message['id']
    if id.startswith(("msg_key:", "message:")):
        dbutil.put(id, message)
    else:
        raise Exception("invalid message id:%s" % id)

def add_message_history(message):
    id_str = message['id']
    prefix, user, timeseq = id_str.split(':')
    new_id = 'msg_history:%s:%s:%s' % (user, timeseq, message.get('version', 0))
    dbutil.put(new_id, message)

@xmanager.listen(["message.updated", "message.add", "message.remove"])
def expire_message_cache(ctx):
    cacheutil.prefix_del("message.count")

def search_message(user_name, key, offset, limit):
    words = []
    for item in key.split(" "):
        if item == "":
            continue
        words.append(item.lower())

    def search_func(key, value):
        if value.content is None:
            return False
        return textutil.contains_all(value.content.lower(), words)

    chatlist = dbutil.prefix_list("message:%s" % user_name, search_func, offset, limit, reverse = True)
    amount   = dbutil.prefix_count("message:%s" % user_name, search_func)
    return chatlist, amount

def delete_message_by_id(id):
    dbutil.delete(id)
    xmanager.fire("message.remove", Storage(id=id))

def db_call(name, *args):
    if xconfig.DB_ENGINE == "sqlite":
        return globals()["rdb_" + name](*args)
    else:
        return globals()["kv_" + name](*args)

@xutils.timeit(name = "Rdb.Message.Count", logfile = True)
def rdb_count_message(user, status):
    count = xtables.get_message_table().count(where="user=$user AND status=$status",
        vars = dict(user = user, status = status))
    return count

@xutils.timeit(name = "Kv.Message.Count", logfile = True)
def kv_count_message(user, status):
    def filter_func(k, v):
        return v.status == status
    return dbutil.prefix_count("message:%s" % user, filter_func = filter_func)

@xutils.cache(prefix="message.count.status", expire=60)
def count_message(user, status):
    return db_call("count_message", user, status)

def get_message_by_id(id):
    if id is None:
        return None
    return dbutil.get(id)


def rdb_list_message_page(user, status, offset, limit):
    db = xtables.get_message_table()
    kw = dict(user=user, status=status)
    chatlist = list(db.select(where=kw, order="ctime DESC", limit=limit, offset=offset))
    amount = db.count(where=kw)
    return chatlist, amount

@xutils.timeit(name = "kv.message.list", logfile = True, logargs = True)
def list_message_page(user, status, offset, limit):
    def filter_func(key, value):
        if status is None:
            return value.user == user
        value.id = key
        return value.user == user and value.status == status
    chatlist = dbutil.prefix_list("message:%s" % user, filter_func, offset, limit, reverse = True)
    amount   = dbutil.prefix_count("message:%s" % user, filter_func)
    return chatlist, amount

def list_file_page(user, offset, limit):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("file://") >= 0
    chatlist = dbutil.prefix_list("message:%s" % user, filter_func, offset, limit, reverse = True)
    # TODO 后续可以用message_stat加速
    amount   = dbutil.prefix_count("message:%s" % user, filter_func)
    return chatlist, amount

def list_link_page(user, offset, limit):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("http://") >= 0 or value.content.find("https://") >= 0
    chatlist = dbutil.prefix_list("message:%s" % user, filter_func, offset, limit, reverse = True)
    # TODO 后续可以用message_stat加速
    amount   = dbutil.prefix_count("message:%s" % user, filter_func)
    return chatlist, amount

def get_filter_by_tag_func(tag):
    def filter_func(key, value):
        if tag is None or tag == "all":
            return True
        if tag == "task":
            # 兼容老版本的数据
            return value.tag == "task" or value.tag == "cron" or value.status == 0 or value.status == 50
        if tag == "done":
            return value.tag == "done" or value.status == 100
        return value.tag == tag
    return filter_func

def list_key(user, offset, limit):
    items = dbutil.prefix_list("msg_key:%s" % user)
    items.sort(key = lambda x: x.mtime, reverse = True)
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

def list_by_tag(user, tag, offset, limit):
    if tag == "key":
        chatlist = list_key(user, offset, limit)
    else:
        filter_func = get_filter_by_tag_func(tag)
        chatlist = dbutil.prefix_list("message:%s" % user, filter_func, offset, limit, reverse = True)

    # 利用message_stat优化count查询
    if tag == "done":
        amount = get_message_stat(user).done_count
    elif tag == "task":
        amount = get_message_stat(user).task_count
    elif tag == "cron":
        amount = get_message_stat(user).cron_count
    elif tag == "log":
        amount = get_message_stat(user).log_count
    elif tag == "key":
        amount = get_message_stat(user).key_count
    else:
        amount = count_by_tag(user, tag)
    return chatlist, amount

def list_by_date(user, date, offset = 0, limit = xconfig.PAGE_SIZE):
    def list_by_date_func(key, value):
        return value.ctime.find(date) == 0

    return dbutil.prefix_list("message:%s" % user, list_by_date_func, offset, limit, reverse = True)

def count_by_tag(user, tag):
    if tag == "key":
        return dbutil.count_table("msg_key:%s" % user)
    if tag == "all":
        return dbutil.count_table("message:%s" % user)
    return dbutil.prefix_count("message:%s" % user, get_filter_by_tag_func(tag))

def get_message_stat0(user):
    value = dbutil.get("user_stat:%s:message" % user)
    if value is None:
        return Storage()
    return value

def get_message_stat(user):
    value = get_message_stat0(user)
    if value is None:
        return refresh_message_stat(user)
    return value

def refresh_message_stat(user):
    # TODO 优化，只需要更新原来的tag和新的tag
    task_count = count_by_tag(user, "task")
    log_count  = count_by_tag(user, "log")
    done_count = count_by_tag(user, "done")
    cron_count = count_by_tag(user, "cron")
    key_count  = count_by_tag(user, "key")
    stat       = get_message_stat0(user)

    stat.task_count = task_count
    stat.log_count  = log_count
    stat.done_count = done_count
    stat.cron_count = cron_count
    stat.key_count  = key_count
    dbutil.put("user_stat:%s:message" % user, stat)
    return stat

def add_search_history(user, search_key, cost_time = 0):
    key = "msg_search_history:%s:%s" % (user, dbutil.timeseq())
    dbutil.put(key, Storage(key = search_key, cost_time = cost_time))

class MessageTag:

    def __init__(self, tag, size):
        self.type = type
        self.size = size
        self.url  = "/message?tag=" + tag
        self.priority = 0
        self.show_next = True
        self.is_deleted = 0
        self.name = "Message"
        self.icon = "fa-file-text-o"
        self.category = None

        if tag == "log":
            self.name = T("memo")
            self.icon = "fa-file-text-o"

        if tag == "task":
            self.name = T("任务")
            self.icon = "fa-calendar-check-o"

def get_message_tag(user, tag):
    msg_stat  = get_message_stat(user)

    if tag == "log":
        return MessageTag(tag, msg_stat.log_count)
    if tag == "task":
        return MessageTag(tag, msg_stat.task_count)

    raise Exception("unknown tag:%s" % tag)

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
xutils.register_func("message.list_by_tag",  list_by_tag)
xutils.register_func("message.list_by_date", list_by_date)

xutils.register_func("message.get_message_stat", get_message_stat)
xutils.register_func("message.refresh_message_stat", refresh_message_stat)
xutils.register_func("message.add_search_history", add_search_history)
xutils.register_func("message.add_history", add_message_history)

