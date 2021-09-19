# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/05/05 11:05:29
# @modified 2021/09/19 13:16:26
# @filename text_parser_properties.py


"""properties文件解析

方法列表

解析properties文件     parse_prop_text(text:str, ret_type="dict") -> {dict|list}

"""

def parse_prop_text(text, ret_type = "dict"):
    """解析key/value格式的配置文本
    @param {string} text 配置文本内容
    @param {string} ret_type 返回的格式，包含list, dict
    """
    if ret_type == 'dict':
        config = dict()
    else:
        config = []

    if text == None or text == "":
        return config

    for line in text.split("\n"):
        line = line.strip()
        if line == "":
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

        if key is None:
            continue

        key = key.strip()
        value = value.strip()

        if ret_type == 'dict':
            config[key] = value
        else:
            config.append(dict(key=key, value=value))

    return config
