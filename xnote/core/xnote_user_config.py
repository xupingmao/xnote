# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/04/06 11:55:29
# @modified 2021/04/11 14:08:02
from xnote.core import xconfig, xauth
from xutils import Storage


class UserConfigItem:

    def __init__(self, key="", label=""):
        self.key = key
        self.label = label

    def get(self, user_name=""):
        return get_user_config(user_name, self.key)
    
    def get_bool(self, user_name=""):
        value = self.get(user_name)
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)
    
    def set(self, user_name="", value=None):
        xauth.update_user_config(user_name=user_name, key=self.key, value=value)

class UserConfig:
    THEME = UserConfigItem("THEME", "主题") 
    HOME_PATH = UserConfigItem("HOME_PATH", "家目录") 
    LANG = UserConfigItem("LANG", "语言")
    nav_style = UserConfigItem("nav_style", "导航风格")
    group_list_order_type = UserConfigItem("group_list_order_type", "笔记本排序方式")
    show_comment_edit = UserConfigItem("show_comment_edit", "是否展示评论编辑")

###### 获取指定用户信息
def get_user_config(user_name, config_key):
    """默认值参考DEFAULT_USER_CONFIG"""
    return xconfig.get_user_config(user_name, config_key)

def get_config_dict(user_name):
    return xauth.get_user_config_dict(user_name)

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


