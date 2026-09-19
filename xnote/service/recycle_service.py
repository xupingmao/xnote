# encoding=utf-8

"""通用的回收站服务(基础服务)

应用层任意模块在删除记录时, 可以调用 RecycleService.add 保存一份 JSON 快照,
用于后续的恢复、审计和按时间归档清理。

主要方法:
- RecycleService.add            记录一条被删除的数据
- RecycleService.get_by_id      查询单条
- RecycleService.list           查询列表(按删除时间倒序)
- RecycleService.count          统计数量
- RecycleService.restore        取出快照内容并标记为已恢复
- RecycleService.delete         彻底删除回收站记录
- RecycleService.clean_before_time  清理某个时间点之前的数据(归档)

使用示例:
    from xnote.service import recycle_service

    recycle_service.add(table_name="todo_task", record_id=task_id,
                        content=todo.to_save_dict(), user_id=user_id,
                        summary=todo.content)

@since 2026/09/19
"""

import logging
from typing import Any, Dict, List, Optional

from xnote.core import xtables
from xutils import dateutil
from xutils import jsonutil
from xutils.base import BaseDataRecord

TABLE_NAME = "recycle_record"


def get_table():
    return xtables.get_table_by_name(TABLE_NAME)


class RecycleRecord(BaseDataRecord):
    """回收站记录"""

    # id 是自增主键, 插入时不参与
    _ignore_save_fields = ["id"]

    def __init__(self):
        self.id = 0
        # 来源表名称
        self.table_name = ""
        # 被删除记录的主键ID
        self.record_id = 0
        # 记录归属的用户ID
        self.user_id = 0
        # 被删除记录的完整内容(json字符串)
        self.content = "{}"
        # 摘要/标题, 列表直接展示, 无需解析content
        self.summary = ""
        # 删除来源, 如 user/system/api
        self.source = ""
        # 执行删除操作的用户ID
        self.operator_id = 0
        # 恢复时间(毫秒时间戳), 0表示未恢复
        self.restore_time = 0
        # 执行恢复操作的用户ID
        self.restore_user_id = 0
        # 扩展字段(json字符串)
        self.extra = "{}"
        # 删除时间(毫秒时间戳), 用于归档
        self.create_time = 0

    def is_restored(self) -> bool:
        return self.restore_time > 0

    def get_content_dict(self) -> Dict[str, Any]:
        """取回被删除记录的内容"""
        try:
            return jsonutil.parse_json_to_dict(self.content or "{}")
        except Exception:
            logging.exception("回收记录 content 解析失败, id=%s", self.id)
            return {}

    def get_extra_dict(self) -> Dict[str, Any]:
        try:
            return jsonutil.parse_json_to_dict(self.extra or "{}")
        except Exception:
            logging.exception("回收记录 extra 解析失败, id=%s", self.id)
            return {}


def _dump_json(value: Any) -> str:
    """序列化为json字符串, jsonutil的encoder支持datetime/bytes等特殊类型"""
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value
    return jsonutil.to_json(value)


class RecycleService:
    """回收站服务, 应用层通过它记录/恢复删除的数据"""

    @classmethod
    def add(cls, table_name: str, record_id: int, content: Any,
            user_id: int = 0, summary: str = "", source: str = "",
            operator_id: int = 0, extra: Any = None) -> int:
        """保存一条被删除的记录

        content 支持 dict(BaseDataRecord 也可以)或者 json 字符串
        返回回收记录的ID
        """
        assert table_name != ""

        if isinstance(content, BaseDataRecord):
            content = content.to_save_dict()

        record = RecycleRecord()
        record.table_name = table_name
        record.record_id = record_id
        record.content = _dump_json(content)
        record.user_id = user_id
        record.summary = summary
        record.source = source
        record.operator_id = operator_id or user_id
        record.extra = _dump_json(extra)
        record.create_time = dateutil.timestamp_ms()

        return get_table().insert_record(record)

    @classmethod
    def get_by_id(cls, id: int) -> Optional[RecycleRecord]:
        return RecycleRecord.from_dict_or_None(
            get_table().select_first(where=dict(id=id)))

    @classmethod
    def _build_where(cls, user_id: int = 0, table_name: str = "",
                     restored: Optional[bool] = None,
                     key: str = "") -> "tuple":
        where = "1=1"
        vars: Dict[str, Any] = {}

        if user_id > 0:
            where += " AND user_id=$user_id"
            vars["user_id"] = user_id

        if table_name != "":
            where += " AND table_name=$table_name"
            vars["table_name"] = table_name

        if restored is not None:
            if restored:
                where += " AND restore_time>0"
            else:
                where += " AND restore_time=0"

        if key != "":
            where += " AND (summary LIKE $key)"
            vars["key"] = "%" + key + "%"

        return where, vars

    @classmethod
    def list(cls, user_id: int = 0, table_name: str = "",
             restored: Optional[bool] = None, key: str = "",
             offset: int = 0, limit: int = 20) -> List[RecycleRecord]:
        """查询回收记录, 默认按删除时间倒序"""
        where, vars = cls._build_where(user_id=user_id, table_name=table_name,
                                       restored=restored, key=key)
        return RecycleRecord.from_dict_list(
            get_table().select(where=where, vars=vars,
                               order="create_time DESC",
                               offset=offset, limit=limit))

    @classmethod
    def count(cls, user_id: int = 0, table_name: str = "",
              restored: Optional[bool] = None, key: str = "") -> int:
        where, vars = cls._build_where(user_id=user_id, table_name=table_name,
                                       restored=restored, key=key)
        return get_table().count(where=where, vars=vars)

    @classmethod
    def restore(cls, id: int, user_id: int = 0) -> Optional[Dict[str, Any]]:
        """取出被删除记录的内容并标记为已恢复

        已经恢复过的记录返回 None (避免重复恢复)
        """
        record = cls.get_by_id(id)
        if record is None:
            return None

        if record.is_restored():
            return None

        get_table().update(where=dict(id=id),
                           restore_time=dateutil.timestamp_ms(),
                           restore_user_id=user_id)

        return record.get_content_dict()

    @classmethod
    def delete(cls, id: int) -> int:
        """彻底删除, 不可恢复"""
        return get_table().delete(where=dict(id=id))

    @classmethod
    def clean_before_time(cls, create_time: int) -> int:
        """清理指定时间之前的数据, 用于归档"""
        assert create_time > 0
        return get_table().delete(where="create_time<$create_time",
                                  vars=dict(create_time=create_time))
