# encoding=utf-8
# @author xupingmao 
# @modified 2021/08/07 17:40:33

'''xnote系统配置
# 用户配置
- get_user_config
- get_user_config_dict

# 文件配置
- 约定目录叫 XXX_DIR
- 文件叫 XXX_FILE

# 通知的配置
- add_notice
- get_notice_list

# 别名配置
- set_alias
- get_alias

# 菜单配置

'''
import os
import time
from collections import OrderedDict
from xutils.base import Storage
from xutils.textutil import Properties

__version__ = "1.0"
__author__ = "xupingmao (578749341@qq.com)"
__copyright__ = "(C) 2016-2021 xupingmao. GNU GPL 3."
__contributors__ = []

# 系统错误信息
errors = []

##################################
# 系统配置项
##################################

# 开发者模式,会展示更多的选项和信息,会开启实验性功能
DEV_MODE           = False
# 开启调试
DEBUG              = False
# 调试盒子模型，针对某些不方便调试的浏览器
DEBUG_HTML_BOX     = False

PORT               = "1234"
SITE_HOME          = None
# 线程数
MIN_THREADS        = 20
# 打开浏览器
OPEN_IN_BROWSER    = False
# 启用数据库的缓存搜索
USE_CACHE_SEARCH   = False
# 文件系统使用urlencode方式,适用于只支持ASCII字符的系统
USE_URLENCODE      = False
# 初始化脚本
INIT_SCRIPT        = "init.py"
# 是否记录位置信息，可通过脚本配置打开
RECORD_LOCATION    = False


# *** 样式设置 ***
# BASE_TEMPLATE = "common/theme/sidebar.html"
BASE_TEMPLATE = "base.html"
# 主题样式
THEME         = "standard"
# 选项风格
OPTION_STYLE  = "aside"
# 页面打开方式
PAGE_OPEN     = "self"
# 页面宽度
PAGE_WIDTH    = "1150"
USER_CSS      = None
USER_JS       = None

# 插件相关 具体的代码参考 handlers/plugins 目录
LOAD_PLUGINS_ON_INIT = True
PLUGINS_DICT         = {}
PLUGIN_TEMPLATE      = ""

# 菜单配置
MENU_LIST    = []
# 导航配置
NAV_LIST     = []
# 笔记的扩展配置
NOTE_OPTIONS = []
# 文件管理器的扩展配置
FS_OPTIONS   = []


##################################
# 存储目录配置项
##################################
# 处理器目录
HANDLERS_DIR = "handlers"
# 工具目录
TOOLS_DIR    = "handlers/tools"
# 语言配置目录
LANG_DIR     = "config/lang"
DB_ENGINE    = "leveldb"

WORKING_DIR  = os.path.dirname(__file__)
WEBDIR       = os.path.join(WORKING_DIR, "static")
PLUGINS_DIR  = os.path.join(WORKING_DIR, "plugins")
LOG_DIR      = os.path.join(WORKING_DIR, "log")
# 日志失效时间
LOG_EXPIRE   = 24 * 3600 * 365
# 用户数据的地址
DATA_PATH   = os.path.join(WORKING_DIR, "data")
DATA_DIR    = DATA_PATH
SCRIPTS_DIR = os.path.join(DATA_DIR, "scripts")
DB_DIR      = os.path.join(DATA_DIR, "db")
CONFIG_DIR  = os.path.join(DATA_DIR, "config")
BACKUP_DIR  = os.path.join(DATA_DIR, "backup")
# 备份失效时间
BACKUP_EXPIRE = 24 * 3600 * 365
# 回收站清理时间
TRASH_EXPIRE  = 24 * 3600 * 90
# 临时文件失效时间
TMP_EXPIRE    = 24 * 3600 * 90
# 删除的笔记有效期
NOTE_REMOVED_EXPIRE = 24 * 3600 * 90

# 其他标记
# 测试用的flag,开启会拥有admin权限
IS_TEST          = False
# 开启性能分析
OPEN_PROFILE     = False
PROFILE_PATH_SET = set(["/file/view"])
# 静音停止时间
MUTE_END_TIME    = None
# 资料相关
# 分页数量
PAGE_SIZE        = 20
# 搜索历史的最大记录数
SEARCH_HISTORY_MAX_SIZE  = 1000
SEARCH_PAGE_SIZE = 20
# 搜索摘要长度
SEARCH_SUMMARY_LEN = 100
RECENT_SEARCH_LIMIT = 10
RECENT_SIZE = 6

IP_BLACK_LIST    = ["192.168.56.1"] # this is vbox ip
# max file size to sync or backup
MAX_FILE_SIZE    = 10 * 1024 ** 2
# 文本编辑器的最大文件限制
MAX_TEXT_SIZE    = 100 * 1024
# 文件系统列分隔符，文件名保留符号参考函数 xutils.get_safe_file_name(filename)
FS_COL_SEP       = "$"
# 是否隐藏系统文件
FS_HIDE_FILES    = True
# 文件管理扩展的选项,类型Storage
FS_LINK          = "/fs_list"
# 文件浏览模式 list/grid/sidebar
FS_VIEW_MODE     = "list"
# 文本文件后缀
FS_TEXT_EXT_LIST = set()
FS_IMG_EXT_LIST  = set()
FS_CODE_EXT_LIST = set()
MIME_TYPES = dict()

# 后面定义的set函数和系统函数冲突了，所以这里创建一个hashset的别名
hashset = set
# 剪切板
FS_CLIP = []

# 通知公告
_notice_list = []
# 搜索历史
search_history = None
# 笔记访问历史
note_history = None

# 配置项
_config = {}

START_TIME = None

# 是否隐藏词典的入口
HIDE_DICT_ENTRY = True


# 默认的用户配置
DEFAULT_USER_CONFIG = {
    "HOME_PATH"   : "/note/group",
    "PROJECT_PATH": "/note/timeline",
    "LANG"        : "zh",
}


def makedirs(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def init(path = DATA_DIR):
    """初始化系统配置项,启动时必须调用"""
    global DATA_PATH
    global DATA_DIR
    global DB_PATH
    global DB_FILE
    global DICT_FILE
    global RECORD_FILE
    global BACKUP_DIR
    global UPLOAD_DIR
    global APP_DIR
    global TMP_DIR
    global DB_DIR
    global SCRIPTS_DIR
    global COMMANDS_DIR
    global PLUGINS_DIR
    global CODE_ZIP
    global DATA_ZIP
    global TRASH_DIR
    global LOG_PATH
    global LOG_DIR
    global LOG_FILE
    global STORAGE_DIR
    global ETC_DIR
    global PLUGIN_TEMPLATE

    DATA_PATH = os.path.abspath(path)
    DATA_DIR  = os.path.abspath(path)
    # 数据库地址
    DB_DIR       = os.path.join(DATA_DIR, "db")
    DB_PATH      = os.path.join(DATA_DIR, "data.db")
    DICT_FILE    = os.path.join(DATA_DIR, "dictionary.db")
    RECORD_FILE  = os.path.join(DATA_DIR, "record.db")
    
    # 备份数据地址
    BACKUP_DIR   = os.path.join(DATA_DIR, "backup")
    # APP地址
    UPLOAD_DIR   = os.path.join(DATA_DIR, "files")
    APP_DIR      = os.path.join(DATA_DIR, "app")
    TMP_DIR      = os.path.join(DATA_DIR, "tmp")
    # 脚本的地址
    SCRIPTS_DIR  = os.path.join(DATA_DIR,    "scripts")
    COMMANDS_DIR = os.path.join(SCRIPTS_DIR, "commands")
    PLUGINS_DIR  = os.path.join(SCRIPTS_DIR, "plugins")
    CODE_ZIP     = os.path.join(DATA_DIR, "code.zip")
    DATA_ZIP     = os.path.join(DATA_DIR, "data.zip")
    TRASH_DIR    = os.path.join(DATA_DIR, "trash")
    LOG_PATH     = os.path.join(DATA_DIR, "xnote.log")
    STORAGE_DIR  = os.path.join(DATA_DIR, "storage")
    ETC_DIR      = os.path.join(DATA_DIR, "storage")
    LOG_DIR      = os.path.join(DATA_DIR, "log")
    DB_FILE      = DB_PATH
    LOG_FILE     = LOG_PATH
    FILE_EXT_PATH = os.path.join(CONFIG_DIR, "file", "type.properties")

    # 一级目录
    makedirs(DATA_DIR)
    makedirs(UPLOAD_DIR)
    makedirs(TMP_DIR)
    makedirs(SCRIPTS_DIR)
    makedirs(TRASH_DIR)
    makedirs(STORAGE_DIR)
    makedirs(ETC_DIR)
    makedirs(LOG_DIR)
    makedirs(DB_DIR)

    # 二级目录
    makedirs(COMMANDS_DIR)
    makedirs(PLUGINS_DIR)

    # 加载文件后缀配置
    load_file_type_config()

    from xutils import fsutil
    PLUGIN_TEMPLATE = fsutil.readfile("./config/plugin/plugin.tpl")

def mark_started():
    global START_TIME
    START_TIME = time.time()

def load_file_type_config0(fpath):
    from xutils import fsutil, textutil
    text  = fsutil.readfile(fpath)
    ext_set = hashset()
    ext_type_dict = textutil.parse_config_text(text, 'dict')
    for ext in ext_type_dict:
        ext_set.add(ext)
    return ext_set

def load_config_as_dict(fpath):
    from xutils import fsutil, textutil
    text  = fsutil.readfile(fpath)
    ext_set = hashset()
    return textutil.parse_config_text(text, 'dict')


def load_file_type_config():
    global FS_TEXT_EXT_LIST
    global FS_IMG_EXT_LIST
    global FS_CODE_EXT_LIST
    global FS_ZIP_EXT_LIST
    global FS_AUDIO_EXT_LIST
    global FS_VIDEO_EXT_LIST
    global MIME_TYPES

    FS_TEXT_EXT_LIST  = load_file_type_config0("./config/file/text.properties")
    FS_IMG_EXT_LIST   = load_file_type_config0("./config/file/image.properties")
    FS_CODE_EXT_LIST  = load_file_type_config0("./config/file/code.properties")
    FS_ZIP_EXT_LIST   = load_file_type_config0("./config/file/zip.properties")
    FS_AUDIO_EXT_LIST = load_file_type_config0("./config/file/audio.properties")
    FS_VIDEO_EXT_LIST = load_file_type_config0("./config/file/video.properties")
    MIME_TYPES        = load_config_as_dict("./config/file/mime-types.properties")
    MIME_TYPES[""]    = "application/octet-stream"


def get_global_config(name, default_value=None):
    """获取配置，如果不存在返回default值"""
    value = _config.get(name)
    if value is not None:
        return value

    value = globals().get(name)
    if value is not None:
        return value

    if value is None:
        return default_value
    return value

def get(key, default_value = None):
    return get_global_config(key, default_value)

def set(name, value):
    """和set函数冲突了，建议使用 set_global_config"""
    return set_global_config(name, value)

def put(name, value):
    return set_global_config(name, value)

def set_global_config(name, value):
    _config[name] = value

def get_config():
    return _config

def has_config(key, subkey = None):
    return has_global_config(key, subkey)

def has(key):
    return has_global_config(key)

def has_global_config(key, subkey = None):
    group_value = get_global_config(key)
    if group_value is None:
        return False
    if subkey is None:
        return True
    return subkey in group_value

def is_mute():
    """是否静音"""
    return MUTE_END_TIME is not None and time.time() < MUTE_END_TIME

# 设置别名
_alias_dict = {}
def set_alias(name, value):
    """设置别名，用于扩展命令"""
    _alias_dict[name] = value

def get_alias(name, default_value):
    """获取别名，用于扩展命令"""
    return _alias_dict.get(name, default_value)


def get_user_config(user_name, config_key, default_value = None):
    """默认值参考DEFAULT_USER_CONFIG"""
    # 未启动，直接返回默认值
    if START_TIME is None:
        return DEFAULT_USER_CONFIG.get(config_key)

    import xauth
    config = xauth.get_user_config_dict(user_name)
    default_value = DEFAULT_USER_CONFIG.get(config_key)
    if config is None:
        return default_value
    else:
        return config.get(config_key, default_value)

def get_user_config_dict(user_name):
    import xauth
    value = xauth.get_user_config_dict(user_name)
    if value is None:
        return Storage()
    return value

def get_current_user_config(key):
    import xauth
    """默认值参考DEFAULT_USER_CONFIG"""
    return get_user_config(xauth.current_name(), key)
