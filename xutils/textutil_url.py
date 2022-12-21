# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/09/11 12:14:28
# @modified 2022/04/16 08:51:27
# @filename textutil_url.py

from urllib.parse import quote

def add_url_param(url, param_key, param_value):
    """给URL增加参数，返回新的URL
    @param {str} url 老的URL
    @param {str} param_key 参数的name
    @param {str} param_value 参数值
    @return {str} 新的URL
    """
    assert type(url) == str
    assert type(param_key) == str
    assert type(param_value) == str

    tail = "%s=%s" % (param_key, quote(param_value))

    if "?" in url:
        return url + "&" + tail
    else:
        return url + "?" + tail

