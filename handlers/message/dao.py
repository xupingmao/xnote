# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/06/12 22:59:33
# @modified 2019/11/23 16:22:20
import xutils
import xconfig
import xmanager
import xtables
from xutils import dbutil, cacheutil, textutil, Storage

def create_message(**kw):
    if xconfig.DB_ENGINE == "sqlite":
        db = xtables.get_message_table()
        return db.insert(**kw)
    else:
        key      = "message:%s:%s" % (kw['user'], dbutil.timeseq())
        kw['id'] = key
        dbutil.put(key, kw)
        return key

@xmanager.listen(["message.updated", "message.add", "message.remove"])
def expire_message_cache(ctx):
    cacheutil.prefix_del("message.count")


def rdb_search_message(user_name, key, offset, limit):
    db   = xtables.get_message_table()
    vars = dict(user= user_name)
    kw = "user = $user"
    start_time = time.time()
    for item in key.split(" "):
        if item == "":
            continue
        kw += " AND content LIKE " + fuzzy_item(item)
    # when find numbers, the sql printed is not correct
    # eg. LIKE '%1%' will be LIKE '%'
    chatlist = list(db.select(where=kw, vars=vars, order="ctime DESC", limit=limit, offset=offset))
    end_time = time.time()
    cost_time = int((end_time-start_time)*1000)
    xutils.trace("MessageSearch", key, cost_time)
    if xconfig.search_history is not None:
        xconfig.search_history.add(key, cost_time)

    amount = db.count(where=kw, vars=vars)
    return chatlist, amount

def search_message(user_name, key, offset, limit):
    words = []
    for item in key.split(" "):
        if item == "":
            continue
        words.append(item)

    def search_func(key, value):
        return value.user == user_name and textutil.contains_all(value.content, words)

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
    return dbutil.get(id)


def rdb_list_message_page(user, status, offset, limit):
    db = xtables.get_message_table()
    kw = dict(user=user, status=status)
    chatlist = list(db.select(where=kw, order="ctime DESC", limit=limit, offset=offset))
    amount = db.count(where=kw)
    return chatlist, amount

@xutils.timeit(name = "kv.message.list", logfile = True, logargs = True)
def kv_list_message_page(user, status, offset, limit):
    def filter_func(key, value):
        if status is None:
            return value.user == user
        value.id = key
        return value.user == user and value.status == status
    chatlist = dbutil.prefix_list("message:%s" % user, filter_func, offset, limit, reverse = True)
    amount   = dbutil.prefix_count("message:%s" % user, filter_func)
    return chatlist, amount

def list_message_page(*args):
    return db_call("list_message_page", *args)

def list_file_page(user, offset, limit):
    def filter_func(key, value):
        if value.content is None:
            return False
        return value.content.find("file://") >= 0
    chatlist = dbutil.prefix_list("message:%s" % user, filter_func, offset, limit, reverse = True)
    amount   = dbutil.prefix_count("message:%s" % user, filter_func)
    return chatlist, amount

xutils.register_func("message.create", create_message)
xutils.register_func("message.search", search_message)
xutils.register_func("message.delete", delete_message_by_id)
xutils.register_func("message.count", count_message)
xutils.register_func("message.find_by_id", get_message_by_id)
xutils.register_func("message.list", list_message_page)
xutils.register_func("message.list_file", list_file_page)

