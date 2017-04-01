# encoding=utf-8
'''system configuration'''
import os

PORT = "1234"
# PORT = "8787"

# 处理器目录
HANDLERS_DIR = "handlers"
# 工具目录
TOOLS_DIR = "handlers/tools"
CONFIG_DIR = os.path.dirname(__file__)
WORKING_DIR = os.path.dirname(CONFIG_DIR)
WEBDIR = os.path.join(WORKING_DIR, "static")
UPLOAD_DIR = os.path.join(WORKING_DIR, "static", "upload")
PLUGINS_DIR = os.path.join(WORKING_DIR, "plugins")
LOG_DIR = os.path.join(WORKING_DIR, "log")
DB_DIR  = os.path.join(WORKING_DIR, "db")
DB_PATH  = os.path.join(WORKING_DIR, "db", "data.db")
SQL_PATH = os.path.join(WORKING_DIR, "db", "data.sql")
BACKUP_DIR = os.path.join(WORKING_DIR, "backup")

IS_ADMIN = False

# 资料相关
# 分页数量
PAGE_SIZE = 10

IP_BLACK_LIST = ["192.168.56.1"] # this is vbox ip

PARTNER_HOST_LIST = [
    "192.168.0.9:8080",
    "192.168.0.21:8080",
    "192.168.0.10:8080"
]

# max file size to sync or backup
MAX_FILE_SIZE = 10 * 1024 ** 2



## 变量

# 导航栏位置
nav_position = "top"


_config = {}

"""
- host ip:port
- 
"""

def get(name, default=None):
    if name in globals():
        return globals()[name]
    if name in _config:
        return _config[name]
        
    if default:
        return default
    return None

def set(name, value):
    _config[name] = value

def get_config():
    return _config
    
def has_config(key, subkey = None):
    group_value = get(key)
    if group_value is None:
        return False
    if subkey is None:
        return True
    return subkey in group_value
    
def has(key):
    return has_config(key)

class XConfig:
    """配置管理器"""

    def __init__(self, fname):
        self.fname = fname

    def load(self):
        pass

    def getvalue(self, section, key, type=None):
        pass

    def setvalue(self, section, key, value):
        pass

    def save(self):
        pass