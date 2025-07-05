# encoding=utf-8
from xutils import dateutil
from xutils import dbutil
from xnote.core.models import CronJobRecord


class CronJobDao:

    db_prefix = "schedule:"

    @classmethod
    def get_by_id(cls, id=""):
        result = dbutil.db_get_object(cls.db_prefix + id)
        return CronJobRecord.from_dict_or_None(result)
    
    @classmethod
    def delete_by_id(cls, id=""):
        return dbutil.db_delete(cls.db_prefix + id)

