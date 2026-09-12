# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 待办(Todo)数据模型，从 message 模块解耦为独立模型
from typing import List, Optional, Union

from xutils.base import BaseDataRecord, BaseEnum, EnumItem
from xutils import dateutil
from xutils import jsonutil


def parse_time_ms(value: Union[None, str, int, float]) -> int:
    """把日期字符串(YYYY-MM-DD[ HH:MM:SS])或时间戳统一成毫秒时间戳，空值返回 0"""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text == "" or text.startswith("0000"):
        return 0
    for fmt in (dateutil.DEFAULT_FORMAT, dateutil.DATE_FORMAT):
        try:
            return int(dateutil.parse_datetime(text, fmt) * 1000)
        except Exception:
            continue
    return 0


def format_time_ms(value: Union[None, str, int, float]) -> str:
    """毫秒时间戳格式化为 YYYY-MM-DD HH:MM:SS，空值返回空字符串

    兼容历史遗留的 datetime 字符串(旧数据未迁移时直接原样展示)。
    """
    if not value:
        return ""
    if isinstance(value, str):
        return "" if value.startswith("0000") else value
    return dateutil.format_millis(value)


def format_date_ms(value: Union[None, str, int, float]) -> str:
    """毫秒时间戳格式化为 YYYY-MM-DD（用于日期输入框），空值返回空字符串"""
    if not value:
        return ""
    if isinstance(value, str):
        return "" if value.startswith("0000") else value[:10]
    return dateutil.format_datetime(value, format="%Y-%m-%d", is_ms=True)


class TodoStatusEnum(BaseEnum):
    """待办状态（库里存英文 code，界面显示中文 label）"""
    not_started = EnumItem("未开始", "not_started")
    in_progress = EnumItem("进行中", "in_progress")
    done = EnumItem("完成", "done")
    canceled = EnumItem("取消", "canceled")


class TodoPriorityEnum(BaseEnum):
    """待办优先级"""
    low = EnumItem("低", "low")
    normal = EnumItem("普通", "normal")
    high = EnumItem("高", "high")
    urgent = EnumItem("紧急", "urgent")


class TodoRecord(BaseDataRecord):
    """待办事项，单表存储(todo_task)。时间字段统一为毫秒时间戳(bigint)"""
    _ignore_save_fields = ["task_id"]

    def __init__(self):
        self.task_id = 0
        self.user = ""
        self.user_id = 0
        self.content = ""
        self.status = TodoStatusEnum.not_started.value
        self.priority = TodoPriorityEnum.normal.value
        self.project_id = 0  # 0 = 未分类/收件箱
        self.begin_time = 0
        self.end_time = 0
        self.done_time = 0
        self.tags = "[]"  # JSON 数组字符串
        self.create_time = 0
        self.update_time = 0
        self.version = 0
        self.is_deleted = 0

    def get_tag_list(self) -> List[str]:
        if not self.tags:
            return []
        try:
            result = jsonutil.from_json(self.tags)
            if isinstance(result, list):
                return result
        except:
            pass
        return []

    def set_tag_list(self, tag_list: List[str]):
        self.tags = jsonutil.to_json(tag_list)
