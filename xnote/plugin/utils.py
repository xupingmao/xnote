from typing import Optional
from xutils import escape_html

class ParamDict:

    """参数字典,在dict的基础上增加了类型方法"""
    def __init__(self, dict_value: dict):
        self._dict = dict_value

    def get_int(self, key: str, default_value=0):
        value = self.get(key)
        if value == "" or value == None:
            return default_value
        return int(value)
    
    def get_float(self, key: str, default_value=0.0):
        value = self.get(key)
        if value == "" or value == None:
            return default_value
        return float(value)
    
    def get_str(self, key: str, default_value="", strip = True):
        result = str(self._dict.get(key, default_value))
        if strip:
            return result.strip()
        return result
    
    def get_bool(self, key: str, default_value=False):
        return bool(self._dict.get(key, default_value))
    
    def get_list(self, key: str, default_value=[]):
        value = self._dict.get(key, default_value)
        if not isinstance(value, list):
            raise Exception(f"expect list but got {type(value)}")
        return value
        
    def get(self, key: str, default_value = None):
        return self._dict.get(key, default_value)
    
    def __str__(self) -> str:
        return str(self._dict)
    
    def check_not_empty(self, key: str):
        value = self.get(key)
        if value == None or value == "":
            raise Exception(f"{key} can not be empty")

