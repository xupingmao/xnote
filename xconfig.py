# encoding=utf-8
'''
system configuration
约定目录叫 XXX_DIR
文件叫 XXX_PATH
'''
import os
import time
from collections import OrderedDict

import xutils

PORT = "1234"
# PORT = "8787"

# 处理器目录
HANDLERS_DIR = "handlers"
# 工具目录
TOOLS_DIR   = "handlers/tools"
WORKING_DIR = os.path.dirname(__file__)
WEBDIR      = os.path.join(WORKING_DIR, "static")
UPLOAD_DIR  = os.path.join(WORKING_DIR, "static", "upload")
PLUGINS_DIR = os.path.join(WORKING_DIR, "plugins")
LOG_DIR     = os.path.join(WORKING_DIR, "log")


# 用户数据的地址

DATA_PATH   = os.path.join(WORKING_DIR, "data")
DATA_DIR    = DATA_PATH
SCRIPTS_DIR = os.path.join(DATA_DIR, "scripts")
DB_DIR      = os.path.join(WORKING_DIR, "db")
CONFIG_DIR  = os.path.join(DATA_DIR, "config")

# 其他标记

# 测试用的flag,开启会拥有admin权限
IS_TEST  = False
# 开启性能分析
OPEN_PROFILE = False
# 静音停止时间
MUTE_END_TIME = None

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

def set_data_path(path):
    global DATA_PATH
    global DATA_DIR
    global DB_PATH
    global BACKUP_DIR
    global APP_DIR
    global TMP_DIR
    global SCRIPTS_DIR
    global CODE_ZIP
    global DATA_ZIP

    xutils.makedirs(path)
    DATA_PATH = path
    DATA_DIR  = path
    # 数据库地址
    DB_PATH    = os.path.join(DATA_PATH, "data.db")
    # 备份数据地址
    BACKUP_DIR = os.path.join(DATA_PATH, "backup")
    # APP地址
    APP_DIR     = os.path.join(DATA_PATH, "app")
    TMP_DIR     = os.path.join(DATA_PATH, "tmp")
    SCRIPTS_DIR = os.path.join(DATA_DIR, "scripts")
    CODE_ZIP    = os.path.join(DATA_DIR, "code.zip")
    DATA_ZIP    = os.path.join(DATA_DIR, "data.zip")

    xutils.makedirs(TMP_DIR)
    xutils.makedirs(SCRIPTS_DIR)

# 初始化默认的Data目录
set_data_path(DATA_PATH)

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
        
class Properties(object): 
    """Properties 文件处理器"""
    def __init__(self, fileName, ordered = True): 
        self.ordered = ordered
        self.fileName = fileName
        self.properties = None
        self.properties_list = None
        self.load_properties()

    def new_dict(self):
        if self.ordered:
            return OrderedDict()
        else:
            return {}

    def _set_dict(self, strName, dict, value): 
        strName = strName.strip()
        value = value.strip()

        if strName == "":
            return

        if(strName.find('.')>0): 
            k = strName.split('.')[0] 
            dict.setdefault(k, self.new_dict()) 
            self._set_dict(strName[len(k)+1:], dict[k], value)
            return
        else: 
            dict[strName] = value 
            return 
    def load_properties(self): 
        self.properties = self.new_dict()
        self.properties_list = self.new_dict()
        with open(self.fileName, 'r', encoding="utf-8") as pro_file: 
            for line in pro_file.readlines(): 
                line = line.strip().replace('\n', '') 
                if line.find("#")!=-1: 
                    line=line[0:line.find('#')] 
                if line.find('=') > 0: 
                    strs = line.split('=') 
                    strs[1]= line[len(strs[0])+1:] 
                    self._set_dict(strs[0], self.properties,strs[1]) 
                    self.properties_list[strs[0].strip()] = strs[1].strip()
        return self.properties

    def get_properties(self):
        return self.properties

    def get_property(self, key, default_value=None):
        return self.properties_list.get(key, default_value)

    def reload(self):
        self.load_properties()

# navigation = Properties("config/navigation.default.properties")
# print(navigation.get_properties())


def is_mute():
    return MUTE_END_TIME is not None and time.time() < MUTE_END_TIME