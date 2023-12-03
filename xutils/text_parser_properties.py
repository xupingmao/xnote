# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/05/05 11:05:29
# @modified 2022/03/06 11:35:51
# @filename text_parser_properties.py


"""properties文件解析

方法列表
========
parse_prop_text_to_pairs(text: str) -> list
    * 解析properties文件成元组对

parse_prop_text_to_dict(text: str) -> dict
    * 解析properties文件成字典

parse_prop_text(text:str, ret_type="dict") -> {dict|list}
    * 解析properties文件
"""

class PropertyFile:
    """property文件
    TODO: 待实现
    """

    def load(self, file):
        pass

    def get_str(self, key="", default_value=""):
        return default_value
    
    def get_int(self, key="", default_value=0):
        return default_value
    
    def get_float(self, key="", default_value=0.0):
        return default_value
    
    def get_list(self, key="", default_value=[]):
        return default_value
    
    def get_dict(self, key="", default_value={}):
        """
        >>> p = PropertFile()
        >>> p.load("a.name=test\na.age=20")
        >>> p.get_dict("a")
        {"name":"test","age":20}
        """
        return default_value

def parse_prop_text_to_pairs(text: str) -> list:
    """解析key/value格式的配置文本
    @param {string} text 配置文本内容
    @param {string} ret_type 返回的格式，包含list, dict
    """
    config = []

    if text == None or text == "":
        return config

    for line in text.split("\n"):
        line = line.strip()
        if line == "":
            continue

        if line.startswith("#"):
            continue

        key = None
        value = None
        
        # 参考Java的Properties文件处理
        # 分隔符 `:` 和 `=`
        # 转义符 \
        # 转义内容 `\t` `\n` `\r` `\f` `\u1111` 
        for i, c in enumerate(line):
            if c == ":" or c == "=":
                key = line[:i]
                value = line[i+1:]
                value = value.split("#", 1)[0]
                break

        if key is None or value is None:
            continue

        key = key.strip()
        value = value.strip()

        config.append(dict(key=key, value=value))

    return config

def parse_prop_text(text, ret_type = "dict"):
    assert ret_type in ("dict", "list")
    pairs = parse_prop_text_to_pairs(text)
    if ret_type == "dict":
        return parse_prop_text_to_dict(text)
    return pairs

def parse_prop_text_to_dict(text):
    pairs = parse_prop_text_to_pairs(text)
    result = dict()
    for item in pairs:
        key = item.get("key")
        value = item.get("value")
        result[key] = value
    return result