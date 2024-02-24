# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-10-27 21:17:40
@LastEditors  : xupingmao
@LastEditTime : 2024-02-14 19:15:31
@FilePath     : /xnote/xnote/core/xconfig.py
@Description  : 描述
"""
# encoding=utf-8
# @author xupingmao
# @modified 2022/03/19 18:10:06
# @filename xconfig.py

'''xnote系统配置

TODO: 系统配置需要注册之后才能使用

# 配置型函数
- init(path = DATA_DIR)

# 全局配置（系统配置）
- get_global_config(key, default_value = None, type = None)
- set_global_config(key, value)

# 用户配置
- get_user_config(user_name, key, default_value = None)
- get_user_config_dict(user_name)

# 文件配置约定
- 目录 XXX_DIR
- 文件 XXX_FILE

# 别名配置
- set_alias
- get_alias

# 菜单配置

'''
import os
import time
import json
import xutils
from xutils import textutil
from xutils import fsutil
from xutils.base import Storage

__version__ = "1.0"
__author__ = "xupingmao (578749341@qq.com)"
__copyright__ = "(C) 2016-2023 xupingmao. GNU GPL 3."
__contributors__ = []

def resolve_config_path(fpath):
    xnote_core_dir = os.path.dirname(__file__)
    xnote_dir = os.path.dirname(xnote_core_dir)
    xnote_root = os.path.dirname(xnote_dir)
    
    # print("xnote_root", xnote_root)
    result = os.path.join(xnote_root, fpath)
    result = os.path.abspath(result)
    # print("result", result)
    return result

# 系统错误信息
errors = []

##################################
# 系统配置项（不建议添加属性，建议通过 set_global_config 设置）
##################################

# 开发者模式,会展示更多的选项和信息,会开启实验性功能
DEV_MODE = False
# 开启调试
DEBUG = False
# 调试盒子模型，针对某些不方便调试的浏览器
DEBUG_HTML_BOX = False

PORT = "1234"
port = PORT

# 线程数
MIN_THREADS = 20
# 打开浏览器
OPEN_IN_BROWSER = False
# 启用数据库的缓存搜索
USE_CACHE_SEARCH = False
# 文件系统使用urlencode方式,适用于只支持ASCII字符的系统
USE_URLENCODE = False
# 初始化脚本
INIT_SCRIPT = "init.py"

# *** 样式设置 ***
# BASE_TEMPLATE = "common/theme/sidebar.html"
BASE_TEMPLATE = "common/base.html"
# 主题样式
THEME = "standard"
# 选项风格
OPTION_STYLE = "aside"
# 页面打开方式
PAGE_OPEN = "self"
# 页面宽度
PAGE_WIDTH = "1150"
USER_CSS = None
USER_JS = None

# 插件相关 具体的代码参考 handlers/plugins 目录
LOAD_PLUGINS_ON_INIT = True
PLUGINS_DICT = {}
PLUGIN_TEMPLATE = ""

# 菜单配置
MENU_LIST = []
# 导航配置
NAV_LIST = []
# 笔记的扩展配置
NOTE_OPTIONS = []
# 文件管理器的扩展配置
FS_OPTIONS = []


##################################
# 存储目录配置项
##################################
# 请求处理器目录
HANDLERS_DIR = resolve_config_path("handlers")
# 工具目录
TOOLS_DIR = resolve_config_path("handlers/tools")
# 语言配置目录
LANG_DIR = resolve_config_path("config/lang")
DB_ENGINE = "leveldb"

WORKING_DIR = os.path.dirname(__file__)
WEBDIR = os.path.join(WORKING_DIR, "static")
PLUGINS_DIR = os.path.join(WORKING_DIR, "plugins")
LOG_DIR = os.path.join(WORKING_DIR, "log")
# 日志失效时间
LOG_EXPIRE = 24 * 3600 * 365
# 用户数据的地址
DATA_PATH = os.path.join(WORKING_DIR, "data")
DATA_DIR = DATA_PATH
SCRIPTS_DIR = os.path.join(DATA_DIR, "scripts")
DB_DIR = os.path.join(DATA_DIR, "db")
CONFIG_DIR = os.path.join(DATA_DIR, "config")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
BACKUP_DB_DIR = os.path.join(BACKUP_DIR, "db")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# 备份失效时间
BACKUP_EXPIRE = 24 * 3600 * 365
# 回收站清理时间
TRASH_EXPIRE = 24 * 3600 * 90
# 临时文件失效时间
TMP_EXPIRE = 24 * 3600 * 90
# 删除的笔记有效期
NOTE_REMOVED_EXPIRE = 24 * 3600 * 90

# 其他标记
# 测试用的flag,开启会拥有admin权限
IS_TEST = False
# 开启性能分析
OPEN_PROFILE = False
PROFILE_PATH_SET = set(["/file/view"])
# 静音停止时间
MUTE_END_TIME = None
# 资料相关
# 分页数量
PAGE_SIZE = 20
# 搜索历史的最大记录数
SEARCH_HISTORY_MAX_SIZE = 1000
SEARCH_PAGE_SIZE = 20
# 搜索摘要长度
SEARCH_SUMMARY_LEN = 100
RECENT_SEARCH_LIMIT = 10
RECENT_SIZE = 6

IP_BLACK_LIST = ["192.168.56.1"]  # this is vbox ip
# max file size to sync or backup
MAX_FILE_SIZE = 10 * 1024 ** 2
# 文本编辑器的最大文件限制
MAX_TEXT_SIZE = 100 * 1024
# 文件系统列分隔符，文件名保留符号参考函数 xutils.get_safe_file_name(filename)
FS_COL_SEP = "$"
# 是否隐藏系统文件
FS_HIDE_FILES = True
# 文件管理扩展的选项,类型Storage
FS_LINK = "/fs_list"
# 文件浏览模式 list/grid/sidebar
FS_VIEW_MODE = "list"
# 文本文件后缀
FS_TEXT_EXT_LIST = set()
FS_IMG_EXT_LIST = set()
FS_CODE_EXT_LIST = set()
MIME_TYPES = dict()

# 后面定义的set函数和系统函数冲突了，所以这里创建一个hashset的别名
hashset = set
# 剪切板
FS_CLIP = []

# 搜索历史
search_history = None
# 笔记访问历史
note_history = None

# 配置项
_config = {}

START_TIME = None

# 是否隐藏词典的入口
HIDE_DICT_ENTRY = True

# 运行时ID
RUNTIME_ID = None
# 退出的编码
EXIT_CODE = 0

class FileReplacement:
    "文件替换符"
    data_dir = "$data"

class FileConfig:

    data_dir = ""
    sqlite_dir = ""
    backup_dir = ""
    backup_db_dir = ""
    db_dir = ""
    files_dir = ""

    boot_lock_file = "" # 启动的锁文件
    record_db_name = "" # 默认的sqlite数据库名称
    record_db_file = "" # 默认的sqlite数据库路径
    kv_db_file = ""

    source_root_dir = "" # 源码根目录
    plugins_dir = "" # 插件目录
    ext_handlers_dir = "./ext_handlers"

    db_backup_expire_days = 5

    template_base_nav_left = "" # 左侧菜单自定义模板
    template_base_nav_top = ""

    @classmethod
    def init(cls, data_dir):
        xnote_core_dir = os.path.dirname(__file__)
        xnote_dir = os.path.dirname(xnote_core_dir)
        cls.source_root_dir = os.path.dirname(xnote_dir)
        
        data_dir = os.path.abspath(data_dir)
        cls.data_dir = os.path.abspath(data_dir)
        makedirs(cls.data_dir)

        cls.files_dir = os.path.join(data_dir, "files")
        makedirs(cls.files_dir)

        cls.db_dir = os.path.join(data_dir, "db")
        
        cls.sqlite_dir = os.path.join(data_dir, "db", "sqlite")
        makedirs(cls.sqlite_dir)

        cls.backup_dir = os.path.join(data_dir, "backup")
        makedirs(cls.backup_dir)

        cls.backup_db_dir = os.path.join(cls.backup_dir, "db")
        makedirs(cls.backup_db_dir)

        cls.record_db_name = SystemConfig.get_str("record_db_name", "record")
        cls.record_db_file = cls.get_db_path(cls.record_db_name)
        cls.kv_db_file = cls.get_db_path("kv_store")
        cls.db_backup_expire_days = SystemConfig.get_int("db_backup_expire_days", 5)
        cls.plugins_dir = os.path.join(cls.data_dir, "scripts", "plugins")
        cls.plugins_upload_dir = os.path.join(cls.plugins_dir, "upload")

        cls.template_base_nav_left = SystemConfig.get_str("template_base_nav_left", "common/nav/base_nav_left.html")
        cls.template_base_nav_top = SystemConfig.get_str("template_base_nav_top", "common/nav/base_nav_top.html")

        cls.boot_lock_file = SystemConfig.get_str("boot_lock_file", "pid.lock")

    @classmethod
    def get_db_path(cls, dbname=""):
        """dbname: sqlite数据库的文件名称"""
        if not dbname.endswith(".db"):
            dbname += ".db"
        return os.path.join(cls.sqlite_dir, dbname)

    @classmethod
    def get_backup_db_path(cls, dbname=""):
        if not dbname.endswith(".db"):
            dbname += ".db"
        return os.path.join(cls.backup_db_dir, dbname)

    @classmethod
    def get_gallery_dir_by_user(cls, user_name=""):
        assert isinstance(user_name, str)
        assert len(user_name) > 0
        return os.path.join(cls.files_dir, user_name, "gallery")

class WebConfig:

    server_home = ""
    port = "1234"

    # 关于系统的链接
    about_url = "" 
    about_text = ""
    login_url = ""

    # 展示配置
    # 是否展示footer
    ui_show_footer = True
    ui_title_prefix = "Xnote"
    # 是否展示translate.js组件
    ui_show_translate_js = False
    
    nav_list = []
    # 自定义导航-开发中
    custom_nav_list = []

    auth_max_session_size = 20

    fast_reload = False

    sync_interval_seconds = 3
    sync_db_from_leader = False
    sync_files_from_leader = False

    # 定时任务开关
    cron_enabled = True

    @classmethod
    def init(cls):
        cls.server_home = SystemConfig.get_str("server_home", "")
        cls.port = SystemConfig.get_str("port", "1234")
        cls.about_url = SystemConfig.get_str("about_url", "/code/wiki/README.md")
        cls.login_url = SystemConfig.get_str("login_url", "/login?target=")
        cls.about_text = SystemConfig.get_str("about_text", "关于Xnote")
        cls.nav_list = cls.load_nav_list()
        cls.auth_max_session_size = SystemConfig.get_int("auth_max_session_size")
        cls.fast_reload = SystemConfig.get_bool("fast_reload", False)

        cls.ui_show_footer = SystemConfig.get_bool("ui_show_footer")
        cls.ui_title_prefix = SystemConfig.get_str("ui_title_prefix", "Xnote")
        cls.ui_show_translate_js = SystemConfig.get_bool("ui_show_translate_js")

        cls.sync_interval_seconds = SystemConfig.get_int("sync_interval_seconds", 3)
        cls.sync_db_from_leader = SystemConfig.get_bool("sync_db_from_leader", False)
        cls.sync_files_from_leader = SystemConfig.get_bool("sync_files_from_leader", False)
        
        cls.cron_enabled = SystemConfig.get_bool("cron_enabled", True)
        cls.force_https = SystemConfig.get_bool("force_https", False)
        cls.record_location = SystemConfig.get_bool("record_location", False)
    
    @classmethod
    def load_nav_list(cls):
        """加载导航列表"""
        if len(cls.nav_list) > 0:
            return cls.nav_list
        nav_list = []
        nav_list.append(NavItem(text="首页", need_logout=True,
                                need_admin=False, url="/system/index"))
        nav_list.append(NavItem(text="首页", need_login=True,
                        need_admin=False, url="/note/index"))
        nav_list.append(NavItem(text="动态", need_login=True,
                        need_admin=False, url="/note/recent?orderby=update"))
        nav_list.append(NavItem(text="分享", need_login=False,
                        need_admin=False, url="/note/public"))
        nav_list.append(NavItem(text="插件", need_login=True,
                        need_admin=False, css_class="desktop-only", url="/plugin_list"))
        nav_list.append(NavItem(text="文件", need_login=True,
                        need_admin=True, css_class="desktop-only", url="/fs_bookmark"))
        nav_list.append(NavItem(text="设置", need_login=True,
                        need_admin=False, url="/system/settings"))
        nav_list.append(NavItem(text="后台", need_login=True,
                        need_admin=True, css_class="desktop-only", url="/system/admin"))
        nav_list.append(NavItem(text="登录", need_logout=True,
                        need_admin=False, url="/login"))
        return nav_list


class TemplateConfig:
    """模板配置"""
    nav_list = []
    lang_dict = {}

    @classmethod
    def init(cls):
        # 加载菜单
        cls.nav_list = WebConfig.load_nav_list()
        cls.load_languages()

    @classmethod
    def load_languages(cls):
        """加载系统语言配置"""
        lang_dict = cls.lang_dict

        lang_dict.clear()
        dirname = LANG_DIR
        for fname in os.listdir(dirname):
            name, ext = os.path.splitext(fname)
            if ext != ".properties":
                continue
            fpath = os.path.join(dirname, fname)
            content = xutils.readfile(fpath)
            config = xutils.parse_config_text(content, ret_type='dict')
            lang_dict[name] = config
        cls.lang_dict = lang_dict

    @classmethod
    def get_lang_mapping(cls, lang):
        if lang == None:
            lang = "zh"
        return cls.lang_dict.get(lang)

class DatabaseConfig:

    db_driver = "" # sqlite/mysql/leveldb/ssdb
    db_driver_cache = "" # memory/redis
    db_driver_sql = "" # sqlite/mysql
    db_driver_kv = ""  # sqlite/mysql/leveldb/ssdb

    user_max_log_size = 500 # 用户日志保留的最大条数
    db_debug = False
    db_log_debug = False
    db_profile_table_proxy = False

    binlog = False
    binlog_max_size = 10000
    # leveldb配置
    block_cache_size = 16 * 1024**2
    write_buffer_size = 4 * 1024**2
    max_open_files = 1000

    # mysql相关配置
    mysql_cloud_type="" # mysql云服务类型
    mysql_database = ""

    # sqlite配置 { DELETE, TRUNCATE, PERSIST, WAL, MEMORY, OFF }
    sqlite_journal_mode = "delete"
    sqlite_page_size = 0
    
    # ssdb相关配置
    ssdb_host = ""
    ssdb_port = 8888

    @classmethod
    def init(cls):
        cls.db_driver = SystemConfig.get_str("db_driver")
        cls.db_driver_cache = SystemConfig.get_str("db_driver_cache", "")
        cls.db_driver_kv = SystemConfig.get_str("db_driver_kv", "")
        cls.db_driver_sql = SystemConfig.get_str("db_driver_sql", "")

        cls.mysql_cloud_type = SystemConfig.get_str("mysql_cloud_type")
        cls.mysql_database = SystemConfig.get_str("mysql_database")
        cls.user_max_log_size = SystemConfig.get_int("user_max_log_size", 500)
        cls.db_debug = SystemConfig.get_bool("db_debug")
        cls.db_log_debug = SystemConfig.get_bool("db_log_debug")
        cls.binlog = SystemConfig.get_bool("binlog")
        cls.binlog_max_size = SystemConfig.get_int("binlog_max_size")
        cls.block_cache_size = SystemConfig.get_int("block_cache_size")
        cls.write_buffer_size = SystemConfig.get_int("write_buffer_size")
        cls.max_open_files = SystemConfig.get_int("max_open_files")
        cls.db_profile_table_proxy = SystemConfig.get_int("db_profile_table_proxy")
        cls.db_sys_log_max_size = SystemConfig.get_int("db_sys_log_max_size", 100000)

        cls.sqlite_journal_mode = SystemConfig.get_str("sqlite_journal_mode", "delete")
        cls.sqlite_page_size = SystemConfig.get_int("sqlite_page_size", 0)

        cls.ssdb_host = SystemConfig.get_str("ssdb_host", "127.0.0.1")
        cls.ssdb_port = SystemConfig.get_int("ssdb_port", 8888)

        if cls.db_driver_sql == "":
            if cls.db_driver == "mysql":
                cls.db_driver_sql = "mysql"
            else:
                cls.db_driver_sql = "sqlite"
        
        if cls.db_driver_kv == "":
            cls.db_driver_kv = cls.db_driver

def read_properties_file(fpath):
    fpath = resolve_config_path(fpath)
    return fsutil.readfile(fpath)


def load_invalid_names():
    fpath = resolve_config_path("./config/user/invalid_names.list")
    return fsutil.load_list_config(fpath)

def load_user_config_properties():
    fpath = resolve_config_path("./config/user/user_config.default.properties")
    return fsutil.load_prop_config(fpath)

def load_cron_config():
    fpath = resolve_config_path("./config/cron/cron.json")
    text = fsutil.readfile(fpath)
    return json.loads(text)

def makedirs(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def make_data_dir(dirname):
    abspath = os.path.join(DATA_DIR, dirname)
    makedirs(abspath)
    return abspath

def init(boot_config_file=None, boot_config_kw = None):
    """初始化系统配置项,启动时必须调用"""
    global DATA_PATH
    global DATA_DIR
    global DB_PATH
    global DB_FILE
    global DICT_FILE
    global RECORD_FILE
    global BACKUP_DIR
    global BACKUP_DB_DIR
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
    global RUNTIME_ID
    global FILE_EXT_PATH
    global CACHE_DIR
    global CONFIG_DIR

    if boot_config_file != None:
        # 初始化启动配置
        init_boot_config(boot_config_file, boot_config_kw=boot_config_kw)

    path = get_system_config("data")
    assert isinstance(path, str)
    DATA_PATH = os.path.abspath(path)
    DATA_DIR = os.path.abspath(path)

    # 初始HTTP端口号
    init_http_port()

    # 初始化文件配置
    FileConfig.init(DATA_DIR)
    # 初始化web配置
    WebConfig.init()
    # 初始化数据库配置
    DatabaseConfig.init()
    # 初始化模板配置
    TemplateConfig.init()

    # 数据库地址
    init_db_config()

    # 备份数据地址
    BACKUP_DIR = make_data_dir("backup")
    BACKUP_DB_DIR = make_data_dir("backup/db")

    # APP地址
    UPLOAD_DIR = make_data_dir("files")
    APP_DIR = make_data_dir("app")
    TMP_DIR = make_data_dir("tmp")
    CACHE_DIR = make_data_dir("cache")

    # 脚本的地址
    SCRIPTS_DIR  = make_data_dir("scripts")
    COMMANDS_DIR = make_data_dir("scripts/commands")
    PLUGINS_DIR  = make_data_dir("scripts/plugins")


    CODE_ZIP = os.path.join(DATA_DIR, "code.zip")
    DATA_ZIP = os.path.join(DATA_DIR, "data.zip")
    TRASH_DIR = os.path.join(DATA_DIR, "trash")
    LOG_PATH = os.path.join(DATA_DIR, "xnote.log")
    STORAGE_DIR = os.path.join(DATA_DIR, "storage")
    ETC_DIR = os.path.join(DATA_DIR, "storage")
    LOG_DIR = os.path.join(DATA_DIR, "log")
    DB_FILE = DB_PATH
    LOG_FILE = LOG_PATH
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

    # 二级目录
    makedirs(COMMANDS_DIR)
    makedirs(PLUGINS_DIR)

    # 加载文件后缀配置
    load_file_type_config()

    # 初始化系统版本配置
    init_system_version()

    PLUGIN_TEMPLATE = read_properties_file("./config/plugin/plugin.tpl.py")

    RUNTIME_ID = textutil.generate_uuid()


def load_default_boot_config():
    # type: () -> dict
    text = read_properties_file("./config/boot/boot.default.properties")
    return textutil.parse_config_text_to_dict(text)


def _parse_int(value):
    assert xutils.is_str(value)
    if value == "":
        return 0

    value = value.lower()
    if value[-2:] == "kb":
        return int(value[:-2]) * 1024

    if value[-2:] == "mb":
        return int(value[:-2]) * 1024**2

    if value[-2:] == "gb":
        return int(value[:-2]) * 1024**3

    if value[-2:] == "tb":
        return int(value[:-2]) * 1024**4

    if value[-2:] == "pb":
        return int(value[:-2]) * 1024**5
    
    if value[-1] == "k":
        return int(value[:-1]) * 1000
    
    if value[-1] == "m":
        return int(value[:-1]) * 1000**2
    
    return int(value)


def init_boot_config(fpath, boot_config_kw=None):

    # 读取默认的配置
    config_dict = load_default_boot_config()


    # 加载用户配置覆盖
    text = fsutil.readfile(fpath)
    user_config = textutil.parse_config_text(text, 'dict')

    config_dict.update(user_config)
    if boot_config_kw != None:
        config_dict.update(boot_config_kw)

    for key in config_dict:
        check_part = textutil.remove_tail(key, ".type")
        if check_part.find(".") >= 0:
            raise Exception("非法的配置项:(%s), 不能包含(.)" % key)

        value = config_dict[key]
        value_type = config_dict.get(key + ".type")

        if value_type == "bool":
            value = (value == "true" or value == "yes")
        if value_type == "int":
            value = _parse_int(value)

        set_global_config("system.%s" % key, value)

    global PORT
    global DEBUG
    global DEV_MODE

    PORT = get_system_config("port")
    DEBUG = get_system_config("debug")

    if DEBUG:
        DEV_MODE = True


def init_http_port():
    port = SystemConfig.get_str("port")

    if port != None:
        # 指定端口优先级最高
        os.environ["PORT"] = port

    if not os.environ.get("PORT"):
        assert isinstance(port, str)
        os.environ["PORT"] = port

    # 兼容
    set_global_config("port", port)


def init_db_config():
    global DB_DIR
    global DB_PATH
    global DICT_FILE
    global RECORD_FILE

    DB_DIR = os.path.join(DATA_DIR, "db")
    DB_PATH = os.path.join(DATA_DIR, "data.db")
    RECORD_FILE = FileConfig.record_db_file

    makedirs(DB_DIR)

    sqlite_dir = os.path.join(DB_DIR, "sqlite")
    makedirs(sqlite_dir)
    DICT_FILE = os.path.join(sqlite_dir, "dictionary.db")


def init_system_version():
    from xutils import fsutil
    fpath = resolve_config_path("./config/version.txt")
    system_version = fsutil.readfile(fpath, limit=1000)
    if system_version != None:
        system_version = system_version.strip()
    set_global_config("system.version", system_version)


def mark_started():
    global START_TIME
    START_TIME = time.time()


def load_file_type_config0(fpath):
    from xutils import fsutil, textutil
    fpath = resolve_config_path(fpath)
    text = fsutil.readfile(fpath)
    ext_set = hashset()
    ext_type_dict = textutil.parse_config_text_to_dict(text)
    for ext in ext_type_dict:
        ext_set.add(ext)
    return ext_set


def load_config_as_dict(fpath):
    # type: (str) -> dict
    from xutils import fsutil, textutil
    fpath = resolve_config_path(fpath)
    text = fsutil.readfile(fpath)
    return textutil.parse_config_text_to_dict(text)

def load_config_as_text(fpath):
    fpath = resolve_config_path(fpath)
    return fsutil.readfile(fpath)

def load_file_type_config():
    global FS_TEXT_EXT_LIST
    global FS_IMG_EXT_LIST
    global FS_CODE_EXT_LIST
    global FS_ZIP_EXT_LIST
    global FS_AUDIO_EXT_LIST
    global FS_VIDEO_EXT_LIST
    global MIME_TYPES

    FS_TEXT_EXT_LIST = load_file_type_config0("./config/file/text.properties")
    FS_IMG_EXT_LIST = load_file_type_config0("./config/file/image.properties")
    FS_CODE_EXT_LIST = load_file_type_config0("./config/file/code.properties")
    FS_ZIP_EXT_LIST = load_file_type_config0("./config/file/zip.properties")
    FS_AUDIO_EXT_LIST = load_file_type_config0(
        "./config/file/audio.properties")
    FS_VIDEO_EXT_LIST = load_file_type_config0(
        "./config/file/video.properties")
    MIME_TYPES = load_config_as_dict("./config/file/mime-types.properties")
    MIME_TYPES[""] = "application/octet-stream"


def get_global_config(name, default_value=None, type=None):
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

def get_system_config(name, default_value=None):
    return get_global_config("system." + name, default_value)

def get_system_config_int(name, default_value = 0):
    value = get_system_config(name, default_value = default_value)
    assert isinstance(value, int)
    return value

def get(key, default_value=None):
    return get_global_config(key, default_value)

def get_str(key, default_value=""):
    value = get(key, default_value=default_value)
    assert isinstance(value, str)
    return value

def set(name, value):
    """和set函数冲突了，建议使用 set_global_config"""
    return set_global_config(name, value)


def put(name, value):
    return set_global_config(name, value)


def set_global_config(name, value):
    _config[name] = value

def set_system_config(name, value):
    set_global_config("system." + name, value)

def get_config():
    raise Exception("deprecated: use xconfig.get_config_dict")

def get_config_dict():
    return _config


def has_config(key, subkey=None):
    return has_global_config(key, subkey)


def has(key):
    return has_global_config(key)


def has_global_config(key, subkey=None):
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


def get_user_config(user_name, config_key, default_value=None):
    """默认值参考DEFAULT_USER_CONFIG"""
    # 未启动，直接返回默认值
    if START_TIME is None:
        return default_value

    from . import xauth
    return xauth.get_user_config(user_name, config_key)


def update_user_config(user_name, key, value):
    from . import xauth
    return xauth.update_user_config(user_name, key, value)


def get_user_config_dict(user_name):
    from . import xauth
    value = xauth.get_user_config_dict(user_name)
    if value is None:
        return Storage()
    return value


def get_current_user_config(key, default_value=None):
    if START_TIME is None:
        return default_value
    
    from . import xauth
    """默认值参考DEFAULT_USER_CONFIG"""
    return get_user_config(xauth.current_name(), key, default_value)


def get_system_dir(name):
    if name == "files":
        return UPLOAD_DIR

    if name == "data":
        return DATA_DIR

    if name == "tmp":
        return TMP_DIR

    if name == "storage":
        return STORAGE_DIR

    if name == "scripts":
        return SCRIPTS_DIR

    if name == "app":
        return APP_DIR

    if name == "archive":
        return os.path.join(DATA_DIR, "archive")
    
    if name == "cache":
        return os.path.join(DATA_DIR, "cache")

    raise Exception("未知的系统目录:" + name)


def get_upload_dir(username):
    if username is None:
        raise Exception("username is None")

    upload_dir_root = get_system_dir("files")
    return os.path.join(upload_dir_root, username, "upload")


def get_backup_dir(name=None):
    if name == None:
        return BACKUP_DIR

    assert isinstance(name, str)
    return os.path.join(BACKUP_DIR, name)

def get_system_files():
    return hashset([
        BACKUP_DB_DIR,
    ])


class SystemConfig:

    @classmethod
    def get_int(cls, name, default_value=0):
        value = get_system_config(name, default_value)
        if value == "":
            return default_value
        if isinstance(value, str):
            value = value.replace("_", "") # 支持 100_000 这种格式
        return int(value)
    
    @classmethod
    def get_str(cls, name, default_value=""):
        value = get_system_config(name, default_value)
        return str(value)

    @classmethod
    def get_bool(cls, name, default_value=False):
        value = get_system_config(name, default_value)
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)

system_config = SystemConfig()




class NavItem:

    def __init__(self, text="", need_login=False, need_logout=False, need_admin=False, url="", css_class=""):
        self.text = text
        self.need_login = need_login
        self.need_logout = need_logout
        self.need_admin = need_admin
        self.url = url
        self.css_class = css_class

    def check_platform(self):
        return True

    def is_visible(self):
        from . import xauth
        # 先判断高权限的
        if self.need_admin:
            return xauth.is_admin() and self.check_platform()

        if self.need_login:
            return xauth.has_login() and self.check_platform()

        if self.need_logout:
            return not xauth.has_login() and self.check_platform()

        return self.check_platform()
    
