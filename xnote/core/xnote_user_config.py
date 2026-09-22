# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/04/06 11:55:29
# @modified 2021/04/11 14:08:02

import typing

from xnote.core import xconfig, xauth
from xutils import Storage


class UserConfigItem:

    def __init__(self, key="", label="", default_value="", help_text=""):
        self.key = key
        self.label = label
        self.default_value = default_value
        self.help_text = help_text

    def get(self, user_name: str):
        return get_user_config(user_name, self.key)
    
    def get_bool(self, user_name=""):
        value = self.get(user_name)
        if isinstance(value, str):
            return value.lower() in ("true", "1")
        return bool(value)
    
    def get_bool_v2(self, user_id: int):
        value = self.get_str(user_id)
        if isinstance(value, str):
            return value.lower() in ("true", "1")
        return bool(value)
    
    def get_str(self, user_id: int):
        if user_id <= 0:
            return self.default_value
        
        value = xauth.get_user_config(user_id=user_id, config_key=self.key, default_value=self.default_value)
        if value is None:
            return self.default_value
        return str(value)
    
    def get_int(self, user_id: int):
        value = self.get_str(user_id)
        try:
            return int(value)
        except:
            return 0
    
    def expire_cache(self, user_id: int):
        xauth.UserMetaDao.expire_cache(user_id=user_id, meta_key=self.key)
    
    def save_config(self, user_id=0, value=None):
        assert user_id > 0
        xauth.update_user_config(user_id=user_id, key=self.key, value=value)

_filter_text_help = """
示例：
类别1 #标签1# #标签2#
类别2 #Tag3# #Tag4#

特殊标签
#_reset# 清空筛选条件
#_all# 选择全部，等同于清空筛选条件
"""

class UserConfig:
    # 主题: default=经典(基础配色), dark=深色, light=浅色
    # 对应的css在 _static/css/theme/ 下, 由 common/script/theme_css.html 按主题名加载
    THEME = UserConfigItem("THEME", "主题", default_value="default") 
    HOME_PATH = UserConfigItem("HOME_PATH", "桌面端首页")
    HOME_PATH_MOBILE = UserConfigItem("HOME_PATH_MOBILE", "移动端首页")
    LANG = UserConfigItem("LANG", "语言/Language")
    nav_style = UserConfigItem("nav_style", "导航风格")
    show_md_preview = UserConfigItem("show_md_preview", "Markdown预览")
    font_scale = UserConfigItem("FONT_SCALE", "字体大小", default_value="100")
    group_list_order_type = UserConfigItem("group_list_order_type", "笔记本排序方式", default_value="0")
    show_comment_edit = UserConfigItem("show_comment_edit", "是否展示评论编辑", default_value="1")
    note_table_width = UserConfigItem("note_table_width", "表格宽度", default_value="normal")
    search_message_detail_show = UserConfigItem("search_message_detail_show", "自动展开记事详情", default_value="0")
    search_plugin_detail_show = UserConfigItem("search_plugin_detail_show", "自动展开插件详情", default_value="0")
    task_filter = UserConfigItem("task.filter", "待办过滤器", help_text=_filter_text_help)
    msg_filter = UserConfigItem("msg.filter", "随手记过滤器", help_text=_filter_text_help)
    calendar_toolbar_tab = UserConfigItem("calendar_toolbar_tab", "日历标签页", default_value="calendar")

    @classmethod
    def init(cls):
        items: typing.List[UserConfigItem] = []
        for value in cls.__dict__.values():
            if isinstance(value, UserConfigItem):
                items.append(value)
                xauth.UserMetaDao.valid_keys.add(value.key)
        cls._items = items

    @classmethod
    def get_by_config_key(cls, config_key: str):
        for item in cls._items:
            if item.key == config_key:
                return item
        return None

###### 获取指定用户信息
def get_user_config(user_name, config_key):
    """默认值参考DEFAULT_USER_CONFIG"""
    return xconfig.get_user_config(user_name, config_key)


class UserConfigDict:

    def __init__(self, user_id: int):
        self.nav_style = UserConfig.nav_style.get_str(user_id)
        self.show_md_preview = UserConfig.show_md_preview.get_str(user_id)
        self.note_table_width = UserConfig.note_table_width.get_str(user_id)
        self.show_comment_edit = UserConfig.show_comment_edit.get_str(user_id)

def get_user_config_dict(user_name):
    if user_name is None or user_name == "":
        return UserConfigDict(0)

    user_id = xauth.UserDao.get_id_by_name(user_name)
    return UserConfigDict(user_id)


get_config_dict = get_user_config_dict

def get_theme(user_name):
    return UserConfig.THEME.get(user_name)

def get_home_path(user_name):
    return UserConfig.HOME_PATH.get(user_name)

def get_project_path(user_name):
    home_path = get_home_path(user_name)
    if home_path == "/note/index":
        return "/note/group"
    return home_path

####### 获取当前用户的信息
def get_current_user_config(key):
    """默认值参考DEFAULT_USER_CONFIG"""
    return get_user_config(xauth.current_name(), key)

def get_current_lang():
    return UserConfig.LANG.get(xauth.current_name_str())

def get_current_project_path():
    return get_project_path(xauth.current_name())

def get_current_home_path():
    return get_home_path(xauth.current_name())


UserConfig.init()
