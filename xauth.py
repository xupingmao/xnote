# encoding=utf-8

try:
    from ConfigParser import ConfigParser
except ImportError as e:
    from configparser import ConfigParser

# 用户配置
_users = None


def get_users():
    global _users

    if _users is not None:
        return _users

    _users = {}
    cf = ConfigParser()
    cf.read("config/users.ini")
    names = cf.sections()
    for name in names:
        options = cf.options(name)
        user = _users[name] = {}
        for option in options:
            user[option] = cf.get(name, option)
        print(name, user)
    return _users

def get_user(name):
    users = get_users()
    return users.get(name)

def get_user_password(name):
    users = get_users()
    return users[name]["password"]

