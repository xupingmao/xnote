from xutils import BaseDataRecord
from xutils import dateutil
from xnote.core import xtables

class SystemLogRecord(BaseDataRecord):
    _ignore_save_fields = ["id"]
    def __init__(self):
        self.id = 0
        self.create_time = 0
        self.log_level = ""
        self.log_type = ""
        self.log_content = ""
        self.cost_time = 0


class SystemLogLevel:
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"

class SystemLogType:
    plugin = "plugin"
    note = "note"
    backup = "backup"

class SystemLogService:

    db = xtables.get_table("system_log")

    @classmethod
    def save_log(cls, log_level: str, log_type: str, log_content: str, cost_time: int = 0):
        record = SystemLogRecord()
        record.create_time = dateutil.timestamp_ms()
        record.log_level = log_level
        record.log_type = log_type
        record.log_content = log_content
        record.cost_time = cost_time
        cls.db.insert_record(record)

    @classmethod
    def get_logs(cls, offset = 0, limit: int = 100):
        rows = cls.db.select(order="id DESC", offset = offset, limit=limit)
        return SystemLogRecord.from_dict_list(rows)
    
    @classmethod
    def count_logs(cls):
        return cls.db.count()
    