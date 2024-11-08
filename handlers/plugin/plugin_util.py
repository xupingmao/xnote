# encoding=utf-8

from xnote.core import xconfig
from xnote.plugin import TextLink

def get_dev_link():
    href = xconfig.WebConfig.server_home + "/plugin_list?category=develop"
    return TextLink(text="开发", href=href)