# encoding=utf-8
from xutils import dateutil
from xutils import dbutil

class CronJobDO:
    def __init__(self):
        self.id = 0
        self.name = ""
        self.url = ""
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.tm_wday = ""
        self.tm_hour = ""
        self.tm_min = ""
        self.message = ""
        self.sound = 0
        self.webpage = 0


class CronJobDao:

    db_prefix = "schedule:"

    @classmethod
    def get_by_id(cls, id=""):
        return dbutil.db_get_object(cls.db_prefix + id)
    
    @classmethod
    def delete_by_id(cls, id=""):
        return dbutil.db_delete(cls.db_prefix + id)

