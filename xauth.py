# encoding=utf-8
import os
import hashlib
import copy

import web
import config

from xutils import ConfigParser
from web.utils import Storage

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
        user = users[name] = Storage()
        user["name"] = name
        for option in options:
            user[option] = cf.get(name, option)
        print(name, user)
    return users

def save_to_ini():
    """保存到配置文件"""
    global _users
    # 先强制同步一次
    _get_users()
    cf = ConfigParser()
    for name in _users:
        user = _users[name]
        cf.add_section(name)
        cf.set(name, "password", user.password)
    with open("config/users.ini", "w") as fp:
        cf.write(fp)
        fp.flush()

    refresh_users()

def _get_users():
    """获取用户，内部接口"""
    global _users

    # 有并发风险
    if _users is not None:
        return _users

    defaults = read_users_from_ini("config/users.default.ini")
    customs  = read_users_from_ini("config/users.ini")

    _users = defaults
    _users.update(customs)
    
    return _users

def get_users():
    """获取所有用户，返回一个深度拷贝版本"""
    return copy.deepcopy(_get_users())


def refresh_users():
    global _users
    _users = None
    print("refresh users")
    return _get_users()

def get_user(name):
    users = _get_users()
    return users.get(name)

def get_user_password(name):
    users = _get_users()
    return users[name]["password"]

def get_current_user():
    return get_user(web.cookies().get("xuser"))

def get_md5_hex(pswd):
    pswd_md5 = hashlib.md5()
    pswd_md5.update(pswd.encode("utf-8"))
    return pswd_md5.hexdigest()

def add_user(name, password):
    users = _get_users()
    user = Storage(name=name, password=password)
    users[name] = user
    save_to_ini()

def has_login(name=None):
    # import threading
    """验证是否登陆

    如果``name``指定,则只能该用户名通过验证
    """
    name_in_cookie = web.cookies().get("xuser")
    pswd_in_cookie = web.cookies().get("xpass")

    # TODO 不同地方调用结果不一致
    # print(name, name_in_cookie)
    if name is not None and name_in_cookie != name:
        return False
    name = name_in_cookie
    if name == "" or name is None:
        return False
    user = get_user(name)
    # print(threading.current_thread().name, " -- User --", user)
    if user is None:
        return False

    return get_md5_hex(user["password"]) == pswd_in_cookie

def is_admin():
    return config.IS_ADMIN or has_login("admin")

def check_login(user_name=None):
    if not has_login(user_name):
        raise web.seeother("/unauthorized")

def login_required(user_name=None):
    """管理员验证装饰器"""
    def _login_required(func):
        def new_func(*args, **kw):
            check_login(user_name)
            ret = func(*args, **kw)
            return ret
        return new_func
    return _login_required

