# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/04/06 11:55:29
# @modified 2020/11/22 13:18:14
import xconfig
import xauth
from xutils import Storage

# 默认的用户配置
DEFAULT_USER_CONFIG = {
    "HOME_PATH"   : "/note/group",
    "PROJECT_PATH": "/note/timeline",
    "LANG"        : "zh",
}

###### 获取指定用户信息
def get_user_config(user_name, config_key):
    """默认值参考DEFAULT_USER_CONFIG"""
    # 未启动，直接返回默认值
    if xconfig.START_TIME is None:
        return DEFAULT_USER_CONFIG.get(config_key)

    config = xauth.get_user_config_dict(user_name)
    default_value = DEFAULT_USER_CONFIG.get(config_key)
    if config is None:
        return default_value
    else:
        return config.get(config_key, default_value)

def get_config_dict(user_name):
    value = xauth.get_user_config_dict(user_name)
    if value is None:
        return Storage()
    return value

def get_theme(user_name):
    return get_user_config(user_name, "THEME")

def get_home_path(user_name):
    return get_user_config(user_name, "HOME_PATH")
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
    return get_current_user_config("LANG")

def get_current_project_path():
    return get_project_path(xauth.current_name())

def get_current_home_path():
    return get_home_path(xauth.current_name())
