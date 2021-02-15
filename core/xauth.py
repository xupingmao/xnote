# encoding=utf-8
import os
import hashlib
import copy
import web
import xconfig
import xutils
import xmanager
from xutils import ConfigParser, textutil, dbutil, fsutil
from xutils import Storage


dbutil.register_table("user", "用户信息表")

config = xconfig
# 用户配置
_users = None
INVALID_NAMES = fsutil.load_set_config("./config/user/invalid_names.list")

def is_valid_username(name):
    """有效的用户名为字母+数字"""
    if name in INVALID_NAMES:
        return False
    return name.isalnum()

def _add_temp_user(temp_users, user_name):
    temp_users[user_name] = Storage(name = user_name, 
        password = "123456",
        salt = "",
        mtime = "",
        token = gen_new_token())

def _get_users(force_reload = False):
    """获取用户，内部接口"""
    global _users

    # 有并发风险
    if _users is not None and not force_reload:
        return _users

    temp_users = {}

    # 初始化默认的用户
    _add_temp_user(temp_users, "admin")
    _add_temp_user(temp_users, "test")

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
        temp_users[name] = user

    _users = temp_users
    return _users

def get_users():
    """获取所有用户，返回一个深度拷贝版本"""
    return copy.deepcopy(_get_users())

def list_user_names():
    users = _get_users()
    return list(users.keys())

def refresh_users():
    xutils.trace("ReLoadUsers", "reload users")
    return _get_users(force_reload = True)

def get_user(name):
    return find_by_name(name)

def find_by_name(name):
    if name is None:
        return None
    users = _get_users()
    name = name.lower()
    user_info = users.get(name)
    if user_info != None:
        return Storage(**user_info)
    return None

def get_user_config_dict(name):
    user = get_user(name)
    if user != None:
        if user.config is None:
            user.config = Storage()
        return user.config
    return None

def get_user_config(user_name, config_key):
    config_dict = get_user_config_dict(user_name)
    if config_dict is None:
        return None
    return config_dict.get(config_key)

def update_user_config_dict(name, config_dict):
    user = get_user(name)
    if user is None:
        return
    config = get_user_config_dict(name)
    config.update(**config_dict)
    user.config = config
    update_user(name, user)

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

def get_user_password_md5(user_name, use_salt = True):
    user     = get_user(user_name)
    password = user.password
    salt     = user.salt

    if use_salt:
        return encode_password(password, salt)
    else:
        return encode_password(password, None)


def current_user():
    if xconfig.IS_TEST:
        return get_user("test")

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

def encode_password(password, salt):
    # 加上日期防止cookie泄露意义不大
    # 考虑使用session失效检测或者定时提醒更新密码
    # password = password + xutils.format_date()
    if password is None:
        password = ""
    pswd_md5 = hashlib.md5()
    pswd_md5.update(password.encode("utf-8"))

    if salt != None:
        pswd_md5.update(salt.encode("utf-8"))
    return pswd_md5.hexdigest()

def write_cookie(name):
    web.setcookie("xuser", name, expires= 24*3600*30)
    pswd_md5 = get_user_password_md5(name)
    web.setcookie("xpass", pswd_md5, expires=24*3600*30)

def get_user_cookie(name):
    return "xuser=%s; xpass=%s;" % (name, get_user_password_md5(name))

def gen_new_token():
    import uuid
    return uuid.uuid4().hex

def add_user(name, password):
    if name == "" or name == None:
        return dict(code = "PARAM_ERROR", message = "name为空")
    if password == "" or password == None:
        return dict(code = "PARAM_ERROR", message = "password为空")
    if not is_valid_username(name):
        return dict(code = "INVALID_NAME", message="非法的用户名")

    name  = name.lower()
    found = find_by_name(name)
    if found is not None:
        return dict(code = "fail", message = "用户已存在")
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
        return dict(code = "success", message = "create success")

def update_user(name, user):
    if name == "" or name == None:
        return
    name = name.lower()

    mem_user = find_by_name(name)
    if mem_user is None:
        raise Exception("user not found")

    password_old = mem_user.get("password")
    mem_user.update(user)

    mem_user.mtime = xutils.format_time()
    if password_old != user.get("password"):
        # 修改密码
        mem_user.salt = textutil.random_string(6)
        mem_user.token = gen_new_token()

    dbutil.put("user:%s" % name, mem_user)
    xutils.trace("UserUpdate", mem_user)

    refresh_users()

    # 刷新完成之后再发送消息
    xmanager.fire("user.update", dict(user_name = name))

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

    password_md5 = encode_password(user["password"], user["salt"])
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

def get_user_data_dir(user_name, mkdirs = False):
    fpath = os.path.join(xconfig.DATA_DIR, "files", user_name)
    if mkdirs:
        fsutil.makedirs(fpath)
    return fpath

xutils.register_func("user.get_config_dict", get_user_config_dict)
xutils.register_func("user.get_config",      get_user_config)

