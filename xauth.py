# encoding=utf-8
import os
import hashlib
import web

import config

try:
    from ConfigParser import ConfigParser
except ImportError as e:
    from configparser import ConfigParser

# 用户配置
_users = None


def read_users_from_ini(path):
    users = {}
    if not os.path.exists(path):
        return users
    cf = ConfigParser()
    cf.read(path, encoding="utf-8")
    names = cf.sections()
    for name in names:
        options = cf.options(name)
        user = users[name] = {}
        user["name"] = name
        for option in options:
            user[option] = cf.get(name, option)
        print(name, user)
    return users

def get_users():
    global _users

    if _users is not None:
        return _users

    defaults = read_users_from_ini("config/users.default.ini")
    customs  = read_users_from_ini("config/users.ini")

    _users = defaults
    _users.update(customs)
    
    return _users


def refresh_users():
    global _users
    _users = None
    return get_users()

def get_user(name):
    users = get_users()
    return users.get(name)

def get_user_password(name):
    users = get_users()
    return users[name]["password"]

def get_current_user():
    return get_user(web.cookies().get("xuser"))


def get_md5_hex(pswd):
    pswd_md5 = hashlib.md5()
    pswd_md5.update(pswd.encode("utf-8"))
    return pswd_md5.hexdigest()

def has_login(name=None):
    """验证是否登陆

    如果``name``指定,则只能该用户名通过验证
    """
    name_in_cookie = web.cookies().get("xuser")
    pswd_in_cookie = web.cookies().get("xpass")

    if name is not None and name_in_cookie != name:
        return False
    name = name_in_cookie
    return get_md5_hex(get_user_password(name)) == pswd_in_cookie

def is_admin():
    return config.IS_ADMIN or has_login("admin")