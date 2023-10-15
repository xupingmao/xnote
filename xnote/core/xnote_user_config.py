# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/04/06 11:55:29
# @modified 2021/04/11 14:08:02
from . import xconfig, xauth
from xutils import Storage

class UserConfigKey:

    THEME = "THEME"         # 主题
    HOME_PATH = "HOME_PATH" # 家目录
    LANG = "LANG"           # 语言
    nav_style = "nav_style" # 导航风格


###### 获取指定用户信息
def get_user_config(user_name, config_key):
    """默认值参考DEFAULT_USER_CONFIG"""
    return xconfig.get_user_config(user_name, config_key)

def get_config_dict(user_name):
    value = xauth.get_user_config_dict(user_name)
    if value is None:
        return Storage()
    return value

def get_theme(user_name):
    return get_user_config(user_name, UserConfigKey.THEME)

def get_home_path(user_name):
    return get_user_config(user_name, UserConfigKey.HOME_PATH)
    # return "/note/category"

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
    return get_current_user_config(UserConfigKey.LANG)

def get_current_project_path():
    return get_project_path(xauth.current_name())

def get_current_home_path():
    return get_home_path(xauth.current_name())
