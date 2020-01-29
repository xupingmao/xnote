# encoding=utf-8
import os
import hashlib
import copy
import web
import xconfig
import xutils
from xutils import ConfigParser, textutil, dbutil, fsutil
from xconfig import Storage

config = xconfig
# 用户配置
_users = None
INVALID_NAMES = fsutil.load_set_config("./config/user/invalid_names.list")

def is_valid_username(name):
    """有效的用户名为字母+数字"""
    if name in INVALID_NAMES:
        return False
    return name.isalnum()


def _get_users():
    """获取用户，内部接口"""
    global _users

    # 有并发风险
    if _users is not None:
        return _users

    _users = {}
    # 默认的账号
    _users["admin"] = Storage(name = "admin", 
        password = "123456", 
        salt = "",
        mtime = "",
        token = gen_new_token())

    user_list = dbutil.prefix_list("user")
    for user in user_list:
        if user.name is None:
            xutils.trace("UserList", "invalid user %s" % user)
            continue
        if isinstance(user.config, dict):
            user.config = Storage(**user.config)
        else:
            user.config = Storage()
        name = user.name.lower()
        _users[name] = user
    return _users

def get_users():
    """获取所有用户，返回一个深度拷贝版本"""
    return copy.deepcopy(_get_users())


def refresh_users():
    global _users
    _users = None
    xutils.trace("ReLoadUsers", "reload users")
    return _get_users()

def get_user(name):
    users = _get_users()
    if xconfig.IS_TEST:
        return users.get("admin")
    return users.get(name)

def get_user_config(name):
    user = get_user(name)
    if user != None:
        if user.config is None:
            user.config = Storage()
        return user.config
    return None

def update_user_config_dict(name, config_dict):
    user = get_user(name)
    if user is None:
        return
    config = get_user_config(user)
    config.update(**config_dict)
    user.config = config
    update_user(name, user)

def find_by_name(name):
    if name is None:
        return None
    name = name.lower()
    return dbutil.get("user:%s" % name)

def select_first(filter_func):
    users = _get_users()
    for item in users.values():
        if filter_func(item):
            return item

def get_user_from_token():
    token = xutils.get_argument("token")
    if token != None and token != "":
        return select_first(lambda x: x.token == token)

def get_user_password(name):
    users = _get_users()
    return users[name]["password"]

def current_user():
    if xconfig.IS_TEST:
        return get_user("admin")
    user = get_user_from_token()
    if user != None:
        return user
    if not hasattr(web.ctx, "env"):
        # 尚未完成初始化
        return None
    xuser = web.cookies().get("xuser")
    if has_login(xuser):
        return get_user(xuser)
    return None
get_current_user = current_user

def current_name():
    """获取当前用户名"""
    user = get_current_user()
    if user is None:
        return None
    return user.get("name")
get_current_name = current_name

def current_role():
    """获取当前用户的角色"""
    user = get_current_user()
    if user is None:
        return None
    name = user.get("name")
    if name == "admin":
        return "admin"
    else:
        return "user"
get_current_role = current_role

def get_md5_hex(pswd):
    pswd_md5 = hashlib.md5()
    pswd_md5.update(pswd.encode("utf-8"))
    return pswd_md5.hexdigest()

def get_password_md5(password, salt):
    # 加上日期防止cookie泄露意义不大
    # 考虑使用session失效检测或者定时提醒更新密码
    # password = password + xutils.format_date()
    if password is None:
        password = ""
    pswd_md5 = hashlib.md5()
    pswd_md5.update(password.encode("utf-8"))
    pswd_md5.update(salt.encode("utf-8"))
    return pswd_md5.hexdigest()

def write_cookie(name):
    web.setcookie("xuser", name, expires= 24*3600*30)
    user     = get_user(name)
    password = user.password
    salt     = user.salt
    pswd_md5 = get_password_md5(password, salt)
    web.setcookie("xpass", pswd_md5, expires=24*3600*30)

def get_user_cookie(name):
    user = get_user(name)
    password = user.get("password")
    salt = user.get("salt")
    return "xuser=%s; xpass=%s;" % (name, get_password_md5(password, salt))

def gen_new_token():
    import uuid
    return uuid.uuid4().hex

def add_user(name, password):
    if name == "" or name == None:
        return
    if password == "" or password == None:
        return
    if not is_valid_username(name):
        return dict(code="INVALID_NAME", message="非法的用户名")

    name  = name.lower()
    found = find_by_name(name)
    if found is not None:
        found.mtime = xutils.format_time()
        found.salt  = textutil.random_string(6)
        found.token = gen_new_token()
        found.password = password
        update_user(name, found)
    else:
        user = Storage(name=name,
            password=password,
            token=gen_new_token(),
            ctime=xutils.format_time(),
            salt=textutil.random_string(6),
            mtime=xutils.format_time())
        dbutil.put("user:%s" % name, user)
        xutils.trace("UserAdd", name)
    refresh_users()

def update_user(name, user):
    if name == "" or name == None:
        return
    name = name.lower()
    mem_user = _users[name]
    mem_user.update(user)

    dbutil.put("user:%s" % name, mem_user)
    xutils.trace("UserUpdate", mem_user)

def remove_user(name):
    if name == "admin":
        return
    name = name.lower()
    dbutil.delete("user:%s" % name)
    refresh_users()

def has_login(name=None):
    """验证是否登陆
    如果``name``指定,则只能该用户名通过验证
    """
    if config.IS_TEST:
        return True
    
    # 优先使用token
    user = get_user_from_token()
    if user != None:
        if name is None:
            return True
        return user.get("name") == name

    cookies = web.cookies()
    name_in_cookie = cookies.get("xuser")
    pswd_in_cookie = cookies.get("xpass")

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

    password_md5 = get_password_md5(user["password"], user["salt"])
    return password_md5 == pswd_in_cookie

def is_admin():
    return config.IS_TEST or has_login("admin")

def check_login(user_name=None):
    if has_login(user_name):
        return
    elif has_login():
        raise web.seeother("/unauthorized")
    # 跳转到登陆URL
    redirect_to_login()

def redirect_to_login():
    path = web.ctx.fullpath
    raise web.seeother("/login?target=" + xutils.encode_uri_component(path))

def login_required(user_name=None):
    """管理员验证装饰器"""
    def deco(func):
        def handle(*args, **kw):
            check_login(user_name)
            ret = func(*args, **kw)
            return ret
        return handle
    return deco

