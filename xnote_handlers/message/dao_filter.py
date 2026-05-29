# encoding=utf-8
# @author xupingmao
# @since 2026/05/29
# @filename dao_filter.py
"""标签过滤器配置的数据访问层"""

from xnote.core import xauth
from xnote.core.xnote_user_config import UserConfig
from xutils import jsonutil
from . import message_utils
from .message_model import TagFilterConfig


def _get_config_item(filter_config_key: str):
    """根据 filter_config_key 获取对应的 UserConfigItem"""
    config_map = {
        "task.filter": UserConfig.task_filter,
        "msg.filter": UserConfig.msg_filter,
    }
    return config_map.get(filter_config_key)


def get_filter_config(user_id: int, filter_config_key: str = "task.filter") -> TagFilterConfig:
    """查询并解析标签过滤器配置"""
    config_item = _get_config_item(filter_config_key)
    if config_item is None:
        return TagFilterConfig()
    config_value = config_item.get_str(user_id)
    return message_utils.parse_filter_config(config_value)


def save_filter_config(user_id: int,
                       tag1_list,
                       tag2_list,
                       tag3_list,
                       filter_config_key: str = "task.filter"):
    """保存标签过滤器配置"""
    config_item = _get_config_item(filter_config_key)
    if config_item is None:
        return None

    config_data = {
        "tag1": tag1_list,
        "tag2": tag2_list,
        "tag3": tag3_list,
    }
    config_value = jsonutil.to_json(config_data, ensure_ascii=False)
    config_item.save_config(user_id=user_id, value=config_value)
    return config_item
