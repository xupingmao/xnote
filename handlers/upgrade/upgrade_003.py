# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/01/01 22:23:26
# @modified 2022/01/08 15:26:03
# @filename upgrade_003.py

"""note_tiny/notebook索引重建"""

import xutils
from xutils import dbutil
from xutils import dateutil
from handlers.upgrade.upgrade_main import log_info, is_upgrade_done, mark_upgrade_done

NOTE_DAO = xutils.DAO("note")

def do_upgrade_book():
    count = 0
    valid_count = 0
    db = dbutil.get_table("notebook")

    for value in db.iter(limit = -1):
        key = value._key
        if value.is_deleted:
            continue

        note_id = value.id
        key_id = key.split(":")[-1]
        if key_id != str(value.id):
            log_info("无效索引: {!r} note_id:{!r}", key_id, note_id)
            NOTE_DAO.update_index(value)
            if value.creator != None:
                db.delete_by_key(key, user_name = value.creator)
            else:
                dbutil.delete(key)
            count += 1
        else:
            valid_count += 1

    log_info("[notebook] 无效索引数量:{}, 有效索引数量:{}", count, valid_count)



def do_upgrade():
    if is_upgrade_done("upgrade_003.2"):
        log_info("upgrade_003 done")
        return

    count = 0
    valid_count = 0
    db = dbutil.get_table("note_tiny")
    for value in db.iter(limit = -1):
        key = value._key
        if value.is_deleted:
            continue

        note_id = value.id
        key_id = key.split(":")[-1]
        if key_id != str(value.id):
            log_info("无效索引: {!r} note_id:{!r}", key_id, note_id)
            NOTE_DAO.update_index(value)
            if value.creator != None:
                db.delete_by_key(key, user_name = value.creator)
            else:
                dbutil.delete(key)
            count += 1
        else:
            valid_count += 1

        if value.creator is None:
            log_info("creator is None, id:{!r}", note_id)
            continue

        db.rebuild_single_index(value, user_name = value.creator)

    do_upgrade_book()

    log_info("[note_tiny] 无效索引数量:{}, 有效索引数量:{}", count, valid_count)

    mark_upgrade_done("upgrade_003.2")



