import logging
import typing

from xnote.core import xtables, xconfig
from xutils import BaseDataRecord
from xutils import DEFAULT_DATETIME
from xutils import dateutil
from web.db import SQLLiteral
from xutils import BaseEnum, EnumItem
from xutils.cacheutil import LocalCacheObject
from xutils import jsonutil

class SystemMetaRecord(BaseDataRecord):
    def __init__(self):
        self.id = 0
        self.create_time = 0
        self.update_time = 0
        self.meta_key = ""
        self.meta_value = ""
        self.version = 0

    def to_save_dict(self):
        result = dict(**self)
        result.pop("id", None)
        return result

class SystemMetaService:

    db = xtables.get_table("system_meta")

    @classmethod
    def save_meta(cls, meta_key: str, meta_value: str):
        now = dateutil.timestamp_ms()
        rowcount = int(cls.db.update(where=dict(meta_key=meta_key), update_time = now, 
                                     meta_value=meta_value, version = SQLLiteral("version+1")))
        if rowcount > 0:
            return
        record = SystemMetaRecord()
        record.meta_key = meta_key
        record.meta_value = meta_value
        record.create_time = dateutil.timestamp_ms()
        record.update_time = dateutil.timestamp_ms()
        cls.db.insert(**record.to_save_dict())

    @classmethod
    def get_meta(cls, meta_key: str):
        record = cls.db.select_first(where = dict(meta_key = meta_key))
        return SystemMetaRecord.from_dict_or_None(record)

    @classmethod
    def get_meta_value(cls, meta_key: str):
        info = cls.get_meta(meta_key)
        if info:
            return info.meta_value
        return None

class SystemMetaEnumItem:

    def __init__(self, meta_name="", meta_key="", default_value=""):
        super().__init__()
        self.meta_name = meta_name
        self.meta_key = meta_key
        self.default_value = default_value
        def load_func():
            logging.info("load meta value, meta_key=%s", meta_key)
            return SystemMetaService.get_meta_value(meta_key=meta_key)
        self._cache = LocalCacheObject(expire_seconds=60, load_func=load_func)

    @property
    def value(self):
        return self.meta_value
    
    def save_meta(self, meta_value: str):
        result = SystemMetaService.save_meta(self.meta_key, meta_value)
        self._cache.expire()
        return result
    
    @property
    def bool_value(self):
        value = self.value
        return value in ("1", "true")
    
    @property
    def list_value(self):
        value = self.value
        if not value:
            return []
        result = jsonutil.fromjson(value)
        assert isinstance(result, list)
        return result
    
    @property
    def meta_value(self):
        cache_value = self._cache.get()
        if cache_value != None:
            return cache_value
        return self.default_value
    
    @property
    def meta_value_int(self):
        if self.meta_value == "":
            return 0
        return int(self.meta_value)
    
    @property
    def meta_value_float(self):
        if self.meta_value == "":
            return 0.0
        return float(self.meta_value)
    
    def expire_cache(self):
        self._cache.expire()

class SystemMetaEnum:
    # 运行状态
    db_backup_file = SystemMetaEnumItem("数据库备份文件", "db.backup.file")
    db_backup_count = SystemMetaEnumItem("数据总量", "db.backup.rows")
    db_backup_binlog_id = SystemMetaEnumItem("备份时的binlog_id", "db.backup.binlog_id")
    db_backup_table_names = SystemMetaEnumItem("备份的表", "db.backup.table_names")
    db_schema_version = SystemMetaEnumItem("数据库schema版本", "db.schema.version")

    # 配置信息
    trace_malloc_enabled = SystemMetaEnumItem("trace_malloc开关", "config.trace_malloc.enabled")
    # SQLite 连接内存采样开关（DAO 入口随机采样，见 xutils.sqlite_mem）
    sqlite_mem_sample_enabled = SystemMetaEnumItem("SQLite内存采样开关", "config.sqlite_mem_sample_enabled.bool", default_value="1")
    page_size = SystemMetaEnumItem("分页大小", "config.page_size.int")
    trash_expire_seconds = SystemMetaEnumItem("回收站清理周期", "config.trash_expire.seconds", default_value=str(3600*24*30))
    fs_hide_files = SystemMetaEnumItem("隐藏系统文件", "config.fs.hide_files.bool")
    fs_max_upload_size = SystemMetaEnumItem(
        "上传文件最大限制", "config.fs.max_upload_size", 
        # 默认20MB
        default_value=str(20*1024**2))
    debug_html_box = SystemMetaEnumItem("调试HTML盒模型", "config.debug_html_box.bool")
    dev_mode = SystemMetaEnumItem("开发者模式", "config.dev_mode.bool")
    init_script = SystemMetaEnumItem("启动脚本", "config.init.script")

    # 集群信息
    leader_base_url = SystemMetaEnumItem("主节点根URL", "leader.base_url")

    @classmethod
    def init(cls):
        items: typing.List[SystemMetaEnumItem] = []
        for value in cls.__dict__.values():
            if isinstance(value, SystemMetaEnumItem):
                items.append(value)
        cls._items = items

    @classmethod
    def get_by_meta_key(cls, meta_key: str):
        for item in cls._items:
            if item.meta_key == meta_key:
                return item
        return None

SystemMetaEnum.init()
xconfig.DEBUG_HTML_BOX = SystemMetaEnum.debug_html_box._cache
xconfig.DEV_MODE = SystemMetaEnum.dev_mode._cache
