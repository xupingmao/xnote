# encoding=utf-8
import os
import hashlib
import copy

import web
import xconfig
import xtables
import xutils

from xutils import ConfigParser
from web.utils import Storage

config = xconfig
# 用户配置
_users = None


def _get_users():
    """获取用户，内部接口"""
    global _users

    # 有并发风险
    if _users is not None:
        return _users

    # defaults = read_users_from_ini("config/users.default.ini")
    # customs  = read_users_from_ini("config/users.ini")
    db = xtables.get_user_table()
    db_users = db.select()
    db_users = list(db_users)

    _users = {}
    # 默认的账号
    _users["admin"] = Storage(name="admin", password="123456")

    # print(db_users)

    for user in db_users:
        _users[user.name] = user
    
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
    if xconfig.IS_TEST:
        return users.get("admin")
    return users.get(name)

def get_user_password(name):
    users = _get_users()
    return users[name]["password"]

def get_current_user():
    if xconfig.IS_TEST:
        return get_user("admin")
    xuser = web.cookies().get("xuser")
    if xuser is None:
        return None
    if has_login(xuser):
        return get_user(xuser)
    return None

def get_current_name():
    """获取当前用户名"""
    user = get_current_user()
    if user is None:
        return None
    return user.get("name")

def get_current_role():
    """获取当前用户的角色"""
    user = get_current_user()
    if user is None:
        return None
    return user.get("name")

def get_md5_hex(pswd):
    pswd_md5 = hashlib.md5()
    pswd_md5.update(pswd.encode("utf-8"))
    return pswd_md5.hexdigest()

def get_password_md5(passwd):
    # 加上日期防止cookie泄露意义不大
    # 考虑使用session失效检测或者定时提醒更新密码
    # passwd = passwd + xutils.format_date()
    pswd_md5 = hashlib.md5()
    pswd_md5.update(passwd.encode("utf-8"))
    return pswd_md5.hexdigest()

def get_admin_cookie():
    password = get_user_password("admin")
    return "xuser=admin; xpass=%s;" % get_password_md5(password)

def add_user(name, password):
    users = _get_users()
    user = Storage(name=name, password=password)
    users[name] = user
    db = xtables.get_user_table()
    exist = db.select_one(where=dict(name=name))
    if exist is None:
        db.insert(name=name,password=password,ctime=xutils.format_time(),mtime=xutils.format_time())
    else:
        db.update(where=dict(name=name), password=password,mtime=xutils.format_time())

def has_login(name=None):
    # import threading
    """验证是否登陆

    如果``name``指定,则只能该用户名通过验证
    """
    if config.IS_TEST:
        return True
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

    password_md5 = get_password_md5(user["password"])
    return password_md5 == pswd_in_cookie

def is_admin():
    return config.IS_TEST or has_login("admin")

def check_login(user_name=None):
    if has_login(user_name):
        return
    elif has_login():
        raise web.seeother("/unauthorized")
    # FIXME 应该是URL
    redirect_to_login()

def redirect_to_login():
    path = web.ctx.fullpath
    raise web.seeother("/login?target=" + xutils.encode_uri_component(path))

def login_required(user_name=None):
    """管理员验证装饰器"""
    def _login_required(func):
        def new_func(*args, **kw):
            check_login(user_name)
            ret = func(*args, **kw)
            return ret
        return new_func
    return _login_required

