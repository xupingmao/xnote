
import logging
import json

from . import base
from xnote.core import xtables
from xnote.core import xauth
from xutils import dbutil
from xutils import dateutil
from xutils.base import BaseDataRecord


def do_upgrade():
    base.execute_upgrade("20260524_comment_data", migrate_comment_data)


# ==================== 复制的表结构定义 ====================
# 注意：复制表结构定义是为了防止未来的表结构变更影响本次迁移

# 老的 KV 表数据结构
class OldCommentRecord(BaseDataRecord):
    """老的 KV 表评论数据结构"""
    def __init__(self, **kw):
        self._id = ""
        self.user = ""
        self.user_id = 0
        self.note_id = ""
        self.type = ""
        self.content = ""
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.pin_level = 0
        self.files = []
        self.update(kw)


# 新的 SQL 表数据结构
class CommentDataRecord(BaseDataRecord):
    """新的 SQL 表评论数据结构"""
    def __init__(self, **kw):
        self.id = 0
        self.create_time = 0
        self.update_time = 0
        self.version = 0
        self.type = ""
        self.user_id = 0
        self.target_id = 0
        self.pin_level = 0
        self.parent_comment_id = 0
        self.content = ""
        self.extra = ""
        self.update(kw)


def migrate_comment_data():
    """从老的 comment KV 表把数据迁移到 comment_data SQL 表"""
    old_db = dbutil.get_table("comment")
    new_db = xtables.get_table_by_name("comment_data")
    
    migrated_count = 0
    
    for item in old_db.iter(limit=-1):
        old_comment = OldCommentRecord(**item)
        new_comment = CommentDataRecord()
        
        # 1. ID 映射
        new_comment.id = int(old_comment._id)
        
        # 2. 时间转换
        # 创建时间转换为毫秒时间戳
        try:
            new_comment.create_time = int(dateutil.parse_datetime(old_comment.ctime) * 1000)
        except:
            new_comment.create_time = dateutil.timestamp_ms()
        
        # 修改时间转换为毫秒时间戳
        try:
            new_comment.update_time = int(dateutil.parse_datetime(old_comment.mtime) * 1000)
        except:
            new_comment.update_time = new_comment.create_time
        
        # 3. 直接映射的字段
        new_comment.type = old_comment.type or ""
        new_comment.content = old_comment.content or ""
        new_comment.pin_level = old_comment.pin_level or 0
        
        # 4. user_id 处理
        new_comment.user_id = old_comment.user_id
        if new_comment.user_id == 0:
            new_comment.user_id = xauth.UserDao.get_id_by_name(old_comment.user)
        
        # 5. note_id -> target_id
        try:
            new_comment.target_id = int(old_comment.note_id)
        except:
            new_comment.target_id = 0
        
        # 6. parent_comment_id 默认为 0
        new_comment.parent_comment_id = 0
        
        # 7. version 默认为 0
        new_comment.version = 0
        
        # 8. 处理 extra 字段，收集 KV 表有但 SQL 表没有的字段
        extra_dict = {}
        
        # 定义 SQL 表已有的字段（用于排除）
        sql_fields = set([
            "_id", "id", "create_time", "update_time",
            "version", "type", "user_id", "target_id",
            "pin_level", "parent_comment_id", "content",
            "extra"
        ])
        
        # 遍历老数据，收集额外字段
        for key, value in item.items():
            if key not in sql_fields:
                extra_dict[key] = value
        
        # 转换为 JSON
        if extra_dict:
            new_comment.extra = json.dumps(extra_dict, ensure_ascii=False)
        
        # 9. 插入或更新
        save_dict = new_comment.to_save_dict()
        existing = new_db.select_first(where=dict(id=new_comment.id))
        if existing:
            new_db.update(**save_dict, where=dict(id=new_comment.id))
        else:
            new_db.insert(**save_dict)
        
        migrated_count += 1
        logging.info("迁移评论成功: id=%s", new_comment.id)
    
    logging.info("迁移评论完成: 成功=%d", migrated_count)
