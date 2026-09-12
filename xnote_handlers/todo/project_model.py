# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/12
# 项目(Project)数据模型，用于按项目维度管理待办
from xutils.base import BaseDataRecord, BaseEnum, EnumItem


# 默认项目名称（迁移时把未分类待办关联到该项目）
DEFAULT_PROJECT_NAME = "默认项目"


class ProjectStatusEnum(BaseEnum):
    """项目状态"""
    active = EnumItem("进行中", "active")
    archived = EnumItem("已归档", "archived")


class ProjectRecord(BaseDataRecord):
    """项目，单表存储(todo_project)。时间字段统一为毫秒时间戳(bigint)"""
    _ignore_save_fields = ["project_id"]

    def __init__(self):
        self.project_id = 0
        self.user_id = 0
        self.name = ""
        self.desc = ""
        self.status = ProjectStatusEnum.active.value
        self.create_time = 0
        self.update_time = 0
