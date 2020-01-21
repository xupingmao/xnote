# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/04/27 02:09:28
# @modified 2020/01/21 01:18:38

import os
import re
import math
import time
import web
import xconfig
import xutils
import xauth
import xmanager
import xtables
import xtemplate
from xtemplate import BasePlugin
from xutils import dbutil, Storage

HTML = """
<!-- Html -->

<div class="card">
    <p>xnote从2.3版本开始，数据库采用leveldb，不再使用sqlite</p>

    <div>
        <a class="btn" href="?action=note_full">迁移笔记主表</a>
        <a class="btn" href="?action=message">迁移待办表</a>
        <a class="btn" href="?action=build_index">构建索引表</a>
        <a class="btn" href="?action=note_tags">迁移标签表</a>
        <a class="btn" href="?action=schedule">迁移任务表</a>
        <a class="btn" href="?action=user">迁移用户表</a>
        <a class="btn" href="?action=search">迁移搜索记录</a>
    </div>

    <div class="top-offset-1">
        {{result}}
        {% if cost > 0 %}
            耗时: {{cost}} ms
        {% end %}
    </div>
</div>
"""

class MigrateHandler(BasePlugin):

    title = "数据迁移"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = None
    editable = False
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 0
        result = ""

        action = xutils.get_argument("action")
        t1 = time.time()

        if action == "note_full":
            result = migrate_note_full()
        if action == "note_history":
            result = migrate_note_history()
        if action == "build_index":
            result = build_index()
        if action == "message":
            result = migrate_message()
        if action == "note_tags":
            result = migrate_note_tags()
        if action == "schedule":
            result = migrate_schedule()
        if action == "user":
            result = migrate_user()
        if action == "search":
            result = migrade_search()

        cost = int((time.time() - t1) * 1000)
        self.writetemplate(HTML, result = result, cost = cost)

def migrate_note_recent():
    recent_list = dbutil.prefix_iter("note_recent", include_key = True)
    for key, item in recent_list:
        dbutil.delete(key)

    for item in dbutil.prefix_iter("note_tiny"):
        if item.type != "group":
            dbutil.zadd("note_recent:%s" % item.creator, item.mtime, item.id)
        if item.is_public:
            dbutil.zadd("note_recent:public", item.mtime, item.id)
    return "迁移完成!"

def migrate_note_history():
    # sqlite to kv
    db = xtables.get_note_history_table()
    for item in db.select():
        dbutil.put("note_history:%s:%s" % (item.note_id, item.version), item)

    # old_key to new_key
    for item in dbutil.prefix_iter("note.history"):
        # 这里leveldb第一版没有note_id，而是id字段
        old_key   = "note.history:%s:%s" % (item.id, item.version)
        new_key   = "note_history:%s:%s" % (item.id, item.version)
        new_value = dbutil.get(new_key)
        if new_value and (new_value.mtime is None or item.mtime > new_value.mtime):
            dbutil.put(new_key, item)
            dbutil.delete(old_key)

        if new_value is None:
            dbutil.put(new_key, item)
            dbutil.delete(old_key)
    return "迁移完成!"

def build_full_note(note, db):
    id = note.id
    result = db.select_first(where=dict(id=id))
    if result is None:
        return

    content = result.get("content", "")
    data = result.get("data", "")
    if content != "":
        note.content = content
    if data != "":
        note.data = data

def build_note_full_key(id):
    return "note_full:%s" % id

def get_note_table():
    try:
        return xtables.get_note_table()
    except:
        # note table is not inited
        return None

def migrate_note_from_db():
    db = get_note_table()
    content_db = xtables.get_note_content_table()
    for item in db.select():
        note_key  = build_note_full_key(item.id)
        ldb_value = dbutil.get(note_key)
        # 如果存在需要比较修改时间
        if ldb_value and item.mtime >= ldb_value.mtime:
            build_full_note(item, content_db)
            dbutil.put(note_key, item)
        
        if ldb_value is None:
            build_full_note(item, content_db)
            dbutil.put(note_key, item)

def migrate_note_full():
    # sqlite to leveldb
    db = get_note_table()
    if db:
        migrate_note_from_db()
    
    # old key to new key
    for item in dbutil.prefix_iter("note.full:"):
        new_key   = build_note_full_key(item.id)
        new_value = dbutil.get(new_key)
        if new_value and item.mtime >= new_value.mtime:
            dbutil.put(new_key, item)
        
        if new_value is None:
            dbutil.put(new_key, item)

    return "迁移完成!"

def put_note_tiny(item):
    key = "note_tiny:%s:%020d" % (item.creator, int(item.id))
    del item.content
    del item.data
    dbutil.put(key, item)

def build_index():
    # 先删除老的索引
    for key, value in dbutil.prefix_iter("note_tiny:", include_key = True):
        dbutil.delete(key)

    # old key to new key
    for item in dbutil.prefix_iter("note_full:"):
        put_note_tiny(item)

    migrate_note_recent()
    return "迁移完成!"

def migrate_note_tags():
    db = xtables.get_file_tag_table()
    count = 0
    for item in db.select():
        note_id = item.file_id
        creator = item.user
        note_key = build_note_full_key(note_id)
        note = dbutil.get(note_key)
        if note != None:
            tag_set = set()
            if note.tags != None:
                tag_set.update(note.tags)
            tag_set.add(item.name)
            note.tags = list(tag_set)

            # 更新入库
            dbutil.put(note_key, note)
            put_note_tiny(note)
            count += 1

    for item in dbutil.prefix_iter("note_tiny"):
        note_id = str(item.id)
        note_tag_key = "note_tags:%s:%s" % (item.creator, note_id)
        note_tag = dbutil.get(note_tag_key)
        if note_tag is None and item.tags != None:
            dbutil.put(note_tag_key, Storage(note_id = note_id, tags = item.tags))
            count += 1

    return "迁移完成,标签数量: %s" % count

def migrate_message():
    db = xtables.get_message_table()
    for item in db.select():
        try:
            unix_timestamp = xutils.parse_time(item.ctime)
        except:
            unix_timestamp = xutils.parse_time(item.ctime, "%Y-%m-%d")
        timestamp = "%020d" % (unix_timestamp * 1000)
        key = "message:%s:%s" % (item.user, timestamp)

        item["old_id"] = item.id
        item["id"] = key
        
        ldb_value = dbutil.get(key)
        put_to_db = False
        if ldb_value and item.mtime >= ldb_value.mtime:
            put_to_db = True
        if ldb_value is None:
            put_to_db = True

        if put_to_db:
            dbutil.put(key, item)
    return "迁移完成!"

def migrate_schedule():
    db = xtables.get_schedule_table()
    for item in db.select():
        key = "schedule:%s" % item.id
        data = dbutil.get(key)
        if data is None:
            dbutil.put(key, item)
    return "迁移完成!"

def migrate_user():
    count = 0
    db = xtables.get_user_table()
    for item in db.select():
        name = item.name.lower()
        key = "user:%s" % name
        data = dbutil.get(key)
        if data is None:
            dbutil.put(key, item)
            count += 1
    return "迁移%s条数据" % count

def migrate_search():
    count = 0
    return "Not Implemented Yet"

SCAN_HTML = """
<div class="card">
    <table class="table">
        {% for key, value in result %}
            <tr>
                <td style="width:20%">{{key}}</td>
                <td style="width:80%">{{value}}</td>
            </tr>
        {% end %}
    </table>
    <a href="?key_from={{last_key}}">下一页</a>
</div>
"""

class DbScanHandler(BasePlugin):

    title = "数据库扫描"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = None

    placeholder = "主键"
    btn_text = "查询"
    editable = False
    show_search = False
    
    def handle(self, input):
        # 输入框的行数
        self.rows = 1
        result = []
        reverse  = xutils.get_argument("reverse") == "true"
        key_from = xutils.get_argument("key_from", "")
        prefix   = xutils.get_argument("prefix", "")
        last_key = [None]

        def func(key, value):
            print("db_scan:", key, value)
            if input in key:
                result.append((key, value))
                if len(result) > 30:
                    last_key[0] = key
                    return False
            return True

        if prefix != "" and prefix != None:
            dbutil.prefix_scan(prefix, func, reverse = reverse)
        else:
            dbutil.scan(key_from = key_from, func = func, reverse = reverse)

        self.writetemplate(SCAN_HTML, result = result, last_key = last_key[0], key = input)


xurls = (
    "/system/db_migrate", MigrateHandler,
    "/system/db_scan", DbScanHandler,
)