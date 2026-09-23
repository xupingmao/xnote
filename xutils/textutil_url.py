# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/09/11 12:14:28
# @modified 2022/04/16 08:51:27
# @filename textutil_url.py

from urllib.parse import quote


def remove_url_param(url: str, param_key: str) -> str:
    """删除URL中的参数(重名参数会被全部删除), 返回新的URL

    只做字符串层面的处理, 不会重新编码其他参数, 避免破坏调用方已有的转义

    @param {str} url 老的URL
    @param {str} param_key 参数的name
    @return {str} 新的URL
    """
    assert isinstance(url, str)
    assert isinstance(param_key, str)

    if "?" not in url:
        return url

    path, _, query = url.partition("?")
    keep_list = []
    for pair in query.split("&"):
        if pair == "":
            continue
        name = pair.split("=", 1)[0]
        if name == param_key:
            continue
        keep_list.append(pair)

    if len(keep_list) == 0:
        # 参数被清空后不再保留 "?" , 避免出现 "?&xxx=1" 这样的URL
        return path

    return path + "?" + "&".join(keep_list)


def add_url_param(url: str, param_key: str, param_value: str):
    """给URL增加参数，返回新的URL

    如果URL中已经存在同名参数，会先删除再追加（替换语义），
    这样重复调用不会出现 `page=1&page=2` 这种情况

    @param {str} url 老的URL
    @param {str} param_key 参数的name
    @param {str} param_value 参数值
    @return {str} 新的URL
    """
    assert isinstance(url, str)
    assert isinstance(param_key, str)
    if not isinstance(param_value, str):
        param_value = str(param_value)

    tail = "%s=%s" % (param_key, quote(param_value))
    url = remove_url_param(url, param_key)

    if "?" in url:
        return url + "&" + tail
    else:
        return url + "?" + tail
