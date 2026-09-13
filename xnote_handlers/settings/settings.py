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
import typing

from xnote.core import xtemplate
from xnote.core import xconfig
from xnote.core import xauth
from xnote.core import xtables
from xnote.core import xmanager
from xnote.core import xnote_user_config
from xutils import sqlite3, Storage, cacheutil
from xnote.core.xtemplate import T
from xutils import logutil, webutil
from xnote.service.system_meta_service import SystemMetaEnum, SystemMetaEnumItem
from xnote_handlers.config import LinkConfig
from xnote.plugin import TextLink
from xnote.webui import ListView, ListViewItem
from xnote.core import xnote_user_config

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

        user_id = xauth.current_user_id()
        category = xutils.get_argument("category", "")

        def get_user_config(key):
            return xauth.get_user_config(user_id, key)

        kw = Storage()
        kw.show_aside = False
        kw.html_title = T("设置")
        kw.title = T("设置")
        kw.parent_link = LinkConfig.app_index
        kw.item_list = item_list
        kw.sys_mem_total  = xutils.format_size(sys_mem_total)
        kw.thread_cnt     = thread_cnt
        kw.xconfig        = xconfig
        kw.category       = category
        kw.search_category = category
        kw.xnote_version  = get_xnote_version()
        kw.start_time     = xconfig.START_TIME
        kw.init_script_url = INIT_SCRIPT_URL
        kw.show_admin_btn = False
        kw.show_back_btn = True
        kw.get_user_config = get_user_config
        kw.SystemInfoEnum = SystemMetaEnum

        if category == "":
            kw.show_back_btn = False

        if xauth.is_admin() and category == "":
            kw.show_admin_btn = True
            kw.right_link = LinkConfig.system_info

        if category == "search":
            kw.html_title = T("搜索设置")
            kw.list_view = self.get_search_list_view()
        elif category == "admin":
            kw.html_title = T("管理员设置")
            kw.list_view = self.get_admin_list_view()
        else:
            kw.html_title = T("设置")
            kw.list_view = self.get_note_list_view()

        return xtemplate.render("settings/page/settings.html", **kw)

    def add_dropdown_config(self, list_view: ListView, info_enum: SystemMetaEnumItem):
        return list_view.add_dropdown(text=info_enum.meta_name, name=info_enum.meta_key, value=info_enum.meta_value)
    
    def add_system_bool_config(self, list_view: ListView, info_enum: SystemMetaEnumItem):
        d = self.add_dropdown_config(list_view, info_enum)
        d.add_option(name="开启", value="1")
        d.add_option(name="关闭", value="0")
        return d
    
    def add_link(self, list_view: ListView, link: TextLink):
        list_view.add_item(ListViewItem(
            text=link.text, href=link.href, 
            css_class="list-item-black", show_chevron_right=True))
    
    def add_text_config(self, list_view: ListView, info_enum: SystemMetaEnumItem):
        list_view.add_item(ListViewItem(
            text=info_enum.meta_name, 
            href=f"/code/edit/config?config_key={info_enum.meta_key}",
            css_class="list-item-black",
            show_chevron_right=True))

    def get_admin_list_view(self):
        result = ListView()
        d = self.add_dropdown_config(result, SystemMetaEnum.page_size)
        d.add_option(name="20", value="20")
        d.add_option(name="30", value="30")
        d.add_option(name="50", value="50")
        d.add_option(name="100", value="100")
        d.add_option(name="200", value="200")

        d = self.add_dropdown_config(result, SystemMetaEnum.trash_expire_seconds)
        d.add_option(name="30天", value=str(3600*24*30))
        d.add_option(name="90天", value=str(3600*24*90))
        d.add_option(name="180天", value=str(3600*24*180))
        d.add_option(name="360天", value=str(3600*24*360))
        
        d = self.add_dropdown_config(result, SystemMetaEnum.fs_max_upload_size)
        d.add_option(name="20MB", value=str(20*1024**2))
        d.add_option(name="100MB", value=str(100*1024**2))

        self.add_system_bool_config(result, SystemMetaEnum.fs_hide_files)
        self.add_system_bool_config(result, SystemMetaEnum.debug_html_box)
        self.add_system_bool_config(result, SystemMetaEnum.dev_mode)
        self.add_system_bool_config(result, SystemMetaEnum.trace_malloc_enabled)

        self.add_link(result, LinkConfig.customized_css)
        self.add_link(result, LinkConfig.customized_js)
        self.add_text_config(result, SystemMetaEnum.init_script)
        self.add_link(result, LinkConfig.system_info)
        
        return result
    
    
    def get_search_list_view(self):
        result = ListView()
        user_id = xauth.current_user_id()
        self.add_user_bool_config(result, xnote_user_config.UserConfig.search_message_detail_show, user_id)
        self.add_user_bool_config(result, xnote_user_config.UserConfig.search_plugin_detail_show, user_id)
        result.add_item(ListViewItem(text="相关词词库", href="/dict/list?dict_type=3", 
                                     css_class="list-item-black",
                                     show_chevron_right=True))
        return result
    
    def add_user_bool_config(self, list_view: ListView, config: xnote_user_config.UserConfigItem, user_id: int):
        value = config.get_str(user_id)
        d = list_view.add_dropdown(text=config.label, name=config.key, value=value, data_type="str")
        d.add_option(name="开启", value="1")
        d.add_option(name="关闭", value="0")

    def add_user_select_config(self, list_view: ListView, config: xnote_user_config.UserConfigItem, user_id: int):
        value = config.get_str(user_id)
        d = list_view.add_dropdown(text=config.label, name=config.key, value=value, data_type="str")
        return d
    

    def get_note_list_view(self):
        result = ListView()
        result.add_item(ListViewItem(text=T("关于系统"), href=xconfig.WebConfig.about_url, 
                                     css_class="list-item-black", show_chevron_right=True))
        result.add_item(ListViewItem(text=T("文件管理"), href="/fs_list", show_chevron_right=True, 
                                     css_class="list-item-black"))
        result.add_item(ListViewItem(text=T("插件管理"), href="/plugin_list", show_chevron_right=True, 
                                     css_class="list-item-black"))

        user_id = xauth.current_user_id()
        d = self.add_user_select_config(result, xnote_user_config.UserConfig.HOME_PATH, user_id)
        d.add_option("笔记本列表", "/note/group")
        d.add_option("功能列表", "/system/index")
        d.add_option("随手记", "/message/log")

        d = self.add_user_select_config(result, xnote_user_config.UserConfig.HOME_PATH_MOBILE, user_id)
        d.add_option("笔记本列表", "/note/group")
        d.add_option("功能列表", "/system/index")
        d.add_option("随手记", "/message/log")

        d = self.add_user_select_config(result, xnote_user_config.UserConfig.font_scale, user_id)
        d.add_option("缩小", "80")
        d.add_option("正常", "100")
        d.add_option("放大", "120")

        d = self.add_user_select_config(result, xnote_user_config.UserConfig.LANG, user_id)
        d.add_option("中文", "zh")
        d.add_option("English", "en")

        d = self.add_user_select_config(result, xnote_user_config.UserConfig.nav_style, user_id)
        d.add_option("顶部导航", "top")
        d.add_option("左侧导航", "left")

        self.add_user_bool_config(result, xnote_user_config.UserConfig.show_md_preview, user_id)
        self.add_user_bool_config(result, xnote_user_config.UserConfig.show_comment_edit, user_id)

        d = self.add_user_select_config(result, xnote_user_config.UserConfig.note_table_width, user_id)
        d.add_option("正常", "normal")
        d.add_option("宽屏", "wide")

        return result


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

def is_user_config_key(key: str):
    return xnote_user_config.UserConfig.get_by_config_key(key) is not None

@xauth.login_required()
def update_user_config(key: str, value: str):
    user_config = xnote_user_config.UserConfig.get_by_config_key(key)
    if user_config is None:
        raise Exception("无效的配置项:%s" % key)
    user_id = xauth.current_user_id()
    user_config.save_config(user_id, value)

@xauth.login_required("admin")
def update_sys_config(key: str, value: str):
    meta = SystemMetaEnum.get_by_meta_key(key)
    if meta:
        meta.save_meta(value)
        return
    else:
        raise Exception(f"meta_key not exists: {key}")

class ConfigHandler:

    def check_value(self, type: str, value: str):
        if type == "int":
            return int(value)

        if type == "bool":
            return value.lower() in ("true", "yes", "on", "1")
        
        return value
    
    def parse_bool(self, value: str):
        return value in ("1", "yes", "true")

    @xauth.login_required()
    def POST(self):
        key   = xutils.get_argument_str("key")
        value = xutils.get_argument_str("value", "")
        type  = xutils.get_argument_str("type")
        p     = xutils.get_argument_str("p")

        update_msg = "%s,%s,%s" % (type, key, value)
        logging.info(update_msg)
        xutils.info("UpdateConfig", update_msg)
        self.check_value(type, value)

        if key in ("DEV_MODE", "DEBUG"):
            xconfig.DEBUG = value
            web.config.debug = self.parse_bool(value)

        try:
            if p == "user" or is_user_config_key(key):
                update_user_config(key, value)
            else:
                update_sys_config(key, value)
        except Exception as e:
            return webutil.FailedResult(code = "fail", message = "设置失败:" + str(e))
            
        return webutil.SuccessResult()

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
