# -*- coding: utf-8 -*-
# @author xupingmao
# @since 2017/02/19
# @modified 2021/12/12 19:46:19
import web
import time
import os
import sys
import platform
import xutils
import logging
import json
import threading
import re
import xtemplate
import xconfig
import xauth
import xtables
import xmanager
from xutils import sqlite3, Storage, cacheutil
from xtemplate import T
from xutils import logutil

try:
    import psutil
except ImportError as e:
    psutil = None

INIT_SCRIPT_URL = "/code/edit?type=script&path=" + str(xconfig.INIT_SCRIPT)
USER_CONFIG_KEY_SET = xauth.get_user_config_valid_keys()

@logutil.timeit_deco(logargs=True,logret=True)
def get_xnote_version():
    return xconfig.get_global_config("system.version")

class Item:
    def __init__(self, key, value):
        self.key   = key
        self.value = value

class SettingsHandler:

    @xauth.login_required()
    def GET(self):
        sys_mem_total     = 0
        thread_cnt        = 0

        thread_cnt = len(threading.enumerate())
        item_list  = [
            Item('软件版本',    get_xnote_version()),
            Item('sqlite版本', sqlite3.sqlite_version if sqlite3 != None else '')
        ]

        user_name = xauth.current_name()
        category = xutils.get_argument("category", "")

        def get_user_config(key):
            return xauth.get_user_config(user_name, key)

        kw = Storage()
        kw.show_aside = False
        kw.html_title = T("设置")
        kw.item_list = item_list
        kw.sys_mem_total  = xutils.format_size(sys_mem_total)
        kw.thread_cnt     = thread_cnt
        kw.xconfig        = xconfig
        kw.category       = category
        kw.xnote_version  = get_xnote_version()
        kw.start_time     = xconfig.START_TIME
        kw.init_script_url = INIT_SCRIPT_URL
        kw.show_admin_btn = False
        kw.show_back_btn = True
        kw.get_user_config = get_user_config

        if category == "":
            kw.show_back_btn = False

        if xauth.is_admin() and category == "":
            kw.show_admin_btn = True

        if category == "search":
            kw.html_title = T("搜索设置")

        if category == "admin":
            kw.html_title = T("管理员设置")

        return xtemplate.render("settings/page/settings.html", **kw)

DEFAULT_SETTINGS = '''

# 导航配置
[NAV_LIST]
About = /code/wiki/README.md


# 索引目录
[INDEX_DIRS]


'''

class PropertiesHandler:
    """基于缓存的配置"""

    @xauth.login_required("admin")
    def GET(self):
        key  = xutils.get_argument("key")
        user = xauth.get_current_name()
        default_value = ""

        if key == "settings":
            default_value = DEFAULT_SETTINGS

        config = Storage(key = key, value = xutils.cache_get("%s@prop_%s" % (user, key), 
            default_value))

        if config is None:
            config = Storage(key=key, value="")
        return xtemplate.render("settings/page/properties.html", 
            show_aside = False,
            config = config)
    
    @xauth.login_required("admin")
    def POST(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")
        user = xauth.get_current_name()
        
        xutils.cache_put("%s@prop_%s" % (user, key), value)

        if key == "settings":
            self.update_settings(value)
        
        config = Storage(key = key, value = value)
        return xtemplate.render("settings/page/properties.html", 
            show_aside = False,
            config = config)

    def update_settings(self, config_text):
        from xutils import ConfigParser

        nav_list = []

        cf = ConfigParser()
        cf.read_string(config_text)
        names = cf.sections()

        options = cf.options('NAV_LIST')
        for option in options:
            value = cf.get('NAV_LIST', option)
            nav_list.append(Storage(name = option, url = value))

        # 处理导航        
        xconfig.NAV_LIST = nav_list


@xauth.login_required()
def update_user_config(key, value):
    if key not in USER_CONFIG_KEY_SET:
        raise Exception("无效的配置项:%s" % key)

    user_name = xauth.current_name()
    config_dict = Storage()
    config_dict[key] = value
    xauth.update_user_config_dict(user_name, config_dict)

@xauth.login_required("admin")
def update_sys_config(key, value):
    setattr(xconfig, key, value)

class ConfigHandler:
    
    @xauth.login_required("admin")
    def POST(self):
        key   = xutils.get_argument("key")
        value = xutils.get_argument_str("value", "")
        type  = xutils.get_argument("type")
        p     = xutils.get_argument("p")

        update_msg = "%s,%s,%s" % (type, key, value)
        logging.info(update_msg)
        xutils.info("UpdateConfig", update_msg)

        if type == "int":
            value = int(value)

        if type == "bool":
            value = value.lower() in ("true", "yes", "on")

        if key == "BASE_TEMPLATE":
            xmanager.reload()

        if key in ("DEV_MODE", "DEBUG"):
            xconfig.DEBUG = value
            xconfig.DEV_MODE = value
            web.config.debug = value

        if key in ("RECENT_SEARCH_LIMIT", "RECENT_SIZE", "PAGE_SIZE", "TRASH_EXPIRE"):
            value = int(value)

        try:
            if p == "user" or key in USER_CONFIG_KEY_SET:
                update_user_config(key, value)
            else:
                update_sys_config(key, value)
        except Exception as e:
            return dict(code = "fail", message = "设置失败:" + str(e))
            
        return dict(code="success")

class HomeEntrySettingsHandler:

    @xauth.login_required()
    def GET(self):
        pass

@xmanager.listen("sys.reload")
def on_reload(ctx = None):
    keys = (
        "THEME", 'FS_HIDE_FILES', 'OPTION_STYLE', 
        'PAGE_OPEN', 'RECENT_SEARCH_LIMIT', 
        "PAGE_SIZE", "RECENT_SIZE",
        "TRASH_EXPIRE",
        "PAGE_WIDTH", "FS_VIEW_MODE",
        "HIDE_DICT_ENTRY"
    )
    for key in keys:
        value = cacheutil.hget('sys.config', key)
        xutils.trace("HGET", "key=%s, value=%s" % (key, value))
        if value is not None:
            setattr(xconfig, key, value)

    # TODO 优化扩展样式和脚本
    css_path = os.path.join(xconfig.SCRIPTS_DIR, "user.css")
    if os.path.exists(css_path): 
        xconfig.USER_CSS = xutils.readfile(css_path)
    
    js_path = os.path.join(xconfig.SCRIPTS_DIR, "user.js")
    if os.path.exists(js_path):
        xconfig.USER_JS = xutils.readfile(js_path)

    # 暂时取消多主题
    # xconfig.THEME = "left"

xurls = (
    r"/settings/index", SettingsHandler,
    r"/settings/entry", HomeEntrySettingsHandler,

    r"/system/settings", SettingsHandler,
    r"/system/properties", PropertiesHandler,
    r"/system/config",  ConfigHandler,
)
