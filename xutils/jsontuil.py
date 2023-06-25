
import json
import uuid
from datetime import datetime
from datetime import date

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, type(bytes)):
            return str(obj, encoding='utf-8')
        elif isinstance(obj,uuid):
            return obj.hex
        else:
            return json.JSONEncoder.default(self, obj)
