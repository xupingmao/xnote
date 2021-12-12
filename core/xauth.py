# encoding=utf-8

"""用户和权限控制,主要的方法包括
- check_login(user_name=None)     检查用户是否登录,可以指定用户或者不指定用户
- login_required(user_name=None)  检查登录态的注解
- current_name()    获取当前登录的用户名，别名 get_current_name()
- current_user()    获取当前登录的用户详情，别名 get_current_user()
- current_role()    获取当前登录的用户角色，别名 get_current_role()
- create_user       创建用户
- update_user       更新用户
- delete_user       删除用户
"""

import os
import hashlib
import copy
import web
import xconfig
import xutils
import xmanager
import warnings
import time
from xutils import ConfigParser, textutil, dbutil, fsutil
from xutils import Storage
from xutils import logutil
from xutils.functions import listremove


dbutil.register_table("user", "用户信息表")
dbutil.register_table("user_config", "用户配置表")
dbutil.register_table("session", "用户会话信息")
dbutil.register_table("user_session_rel", "用户会话关系")

USER_TABLE = dbutil.get_table("user")

# 用户配置
# 通过init方法完成初始化
BUILTIN_USER_DICT = None
_USER_LIST       = None
NAME_LENGTH_MIN  = 4
PASSWORD_LEN_MIN = 6
INVALID_NAMES    = fsutil.load_set_config("./config/user/invalid_names.list")
USER_CONFIG_PROP = fsutil.load_prop_config("./config/user/user_config.default.properties")
MAX_SESSION_SIZE = 20
SESSION_EXPIRE   = 24 * 3600 * 7
PRINT_DEBUG_LOG  = False

class UserModel:
    # TODO 用户模型
    name = "登录名"
    password = "密码"
    token = "授权令牌"
    ctime = "创建时间"
    mtime = "修改时间"
    login_time = "登录时间"

def _is_debug_enabled():
    return PRINT_DEBUG_LOG

def log_debug(fmt, *args):
    if PRINT_DEBUG_LOG:
        print("[xauth]", fmt.format(*args))

def is_valid_username(name):
    """有效的用户名为字母+数字"""
    if name in INVALID_NAMES:
        return False
    if len(name) < NAME_LENGTH_MIN:
        return False
    return name.isalnum()

def validate_password_error(password):
    if len(password) < PASSWORD_LEN_MIN:
        return "密码不能少于6位"
    return None

def _create_temp_user(temp_users, user_name):
    temp_users[user_name] = Storage(name = user_name, 
        password = "123456",
        salt = "",
        mtime = "",
        token = gen_new_token())

def _get_users(force_reload = False):
    """获取用户，内部接口"""
    global _USER_LIST

    # 有并发风险
    if _USER_LIST is not None and not force_reload:
        return _USER_LIST

    temp_users = {}

    # 初始化默认的用户
    _create_temp_user(temp_users, "admin")
    _create_temp_user(temp_users, "test")

    user_list = USER_TABLE.list(offset = 0, limit = 20)
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

    _USER_LIST = temp_users
    return _USER_LIST

def _setcookie(key, value, expires=24*3600*30):
    assert isinstance(key, str)
    assert isinstance(value, str)
    web.setcookie(key, value, expires)

def get_users():
    """获取所有用户，返回一个深度拷贝版本"""
    warnings.warn("get_users已经过时，请停止使用", DeprecationWarning)
    return copy.deepcopy(_get_users())

def list_user_names():
    users = _get_users()
    return list(users.keys())

def refresh_users():
    xutils.trace("ReLoadUsers", "reload users")
    return _get_users(force_reload = True)

def get_user(name):
    warnings.warn("get_user已经过时，请使用 get_user_by_name", DeprecationWarning)
    return find_by_name(name)

def get_user_by_name(user_name):
    return find_by_name(user_name)

def create_uuid():
    import uuid
    return uuid.uuid4().hex

def get_valid_session_by_id(sid):
    session_info = dbutil.get("session:%s" % sid)
    if session_info is None:
        return None

    if session_info.user_name is None:
        dbutil.delete("session:%s" % sid)
        return None

    if time.time() > session_info.expire_time:
        dbutil.delete("session:%s" % sid)
        return None

    return session_info

def list_user_session_id(user_name):
    session_id_list = dbutil.get("user_session_rel:%s" % user_name)
    if session_id_list is None:
        return []

    expire_id_set = set()
    for sid in session_id_list:
        session_info = get_valid_session_by_id(sid)
        if session_info is None:
            expire_id_set.add(sid)

    for sid in expire_id_set:
        listremove(session_id_list, sid)

    return session_id_list

def list_user_session_detail(user_name):
    session_id_list = list_user_session_id(user_name)
    session_detail_list = []
    for sid in session_id_list:
        detail = get_valid_session_by_id(sid)
        if detail != None:
            session_detail_list.append(detail)
    return session_detail_list

def create_user_session(user_name, expires = SESSION_EXPIRE, login_ip = None):
    user_detail = get_user_by_name(user_name)
    if user_detail is None:
        raise Exception("user not found: %s" % user_name)

    session_id = create_uuid()

    session_id_list = list_user_session_id(user_name)

    if len(session_id_list) > MAX_SESSION_SIZE:
        # TODO 踢出最早的登录
        raise Exception("user login too many devices: %s" % user_name)

    # 保存用户和会话关系
    session_id_list.append(session_id)
    dbutil.put("user_session_rel:%s" % user_name, session_id_list)

    # 保存会话信息
    session_info = Storage(user_name = user_name, 
        sid   = session_id,
        token = user_detail.token, 
        login_time  = time.time(),
        login_ip = login_ip,
        expire_time = time.time() + expires)
    dbutil.put("session:%s" % session_id, session_info)

    print("session_info:", session_info)
    return session_id

def delete_user_session_by_id(sid):
    # 登录的时候会自动清理无效的sid关系
    dbutil.delete("session:%s" % sid)

def _get_user_from_db(name):
    user_detail = USER_TABLE.get_by_key("user:" + name)
    return user_detail

def _get_builtin_user(name):
    assert BUILTIN_USER_DICT != None
    return BUILTIN_USER_DICT.get(name)

def find_by_name(name):
    if name is None:
        return None

    user = _get_user_from_db(name)
    if user != None:
        return user
    return _get_builtin_user(name)

def get_user_config_db(name):
    assert name != None
    assert name != ""
    return dbutil.get_hash_table("user_config", user_name = name)

def get_user_config_dict(name):
    if name is None or name == "":
        return None

    db = get_user_config_db(name)

    config_dict = db.dict(limit = -1)
    if len(config_dict) > 0:
        return config_dict

    user = get_user_by_name(name)
    if user != None:
        if user.config is None:
            user.config = Storage()
        elif isinstance(user.config, dict):
            user.config = Storage(**user.config)
        return user.config
    return None

def get_user_config_valid_keys():
    return USER_CONFIG_PROP.keys()

def get_user_config(user_name, config_key):
    default_value = USER_CONFIG_PROP.get(config_key)
    config_dict = get_user_config_dict(user_name)
    if config_dict is None:
        return default_value
    return config_dict.get(config_key, default_value)

def update_user_config_dict(name, config_dict):
    user = get_user(name)
    if user is None:
        return

    for key in config_dict:
        if key not in USER_CONFIG_PROP:
            raise Exception("invalid user config: %s" % key)

    db = get_user_config_db(name)

    for key in config_dict:
        value = config_dict.get(key)
        db.put(key, value)

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

def get_session_id_from_cookie():
    cookies = web.cookies()
    return cookies.get("sid")

def get_user_from_cookie():
    session_id = get_session_id_from_cookie()
    session_info = get_valid_session_by_id(session_id)

    if session_info is None:
        return None

    log_debug("get_user_from_cookie: sid={}, session_info={}", session_id, session_info)

    return get_user_by_name(session_info.user_name)

def get_current_user():
    if xconfig.IS_TEST:
        return get_user_by_name("test")

    user = get_user_from_token()
    if user != None:
        return user
    if not hasattr(web.ctx, "env"):
        # 尚未完成初始化
        return None
    return get_user_from_cookie()

def current_user():
    return get_current_user()

def get_current_name():
    """获取当前用户名"""
    user = get_current_user()
    if user is None:
        return None
    return user.get("name")

def current_name():
    return get_current_name()

def get_current_role():
    """获取当前用户的角色"""
    user = get_current_user()
    if user is None:
        return None
    name = user.get("name")
    if name == "admin":
        return "admin"
    else:
        return "user"

def current_role():
    return get_current_role()

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

def write_cookie(user_name):
    session_id = create_user_session(user_name)
    _setcookie("sid", session_id, expires=24*3600*30)


def get_user_cookie(name):
    session_list = list_user_session_detail(name)

    if len(session_list) == 0:
        sid = create_user_session(name, login_ip = "system")
    else:
        sid = session_list[0].sid

    return "sid=%s" % sid

def gen_new_token():
    import uuid
    return uuid.uuid4().hex

def create_user(name, password):
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

def _check_password(password):
    error = validate_password_error(password)
    if error != None:
        raise Exception(error)

def update_user(name, user):
    if name == "" or name == None:
        return
    name = name.lower()

    mem_user = find_by_name(name)
    if mem_user is None:
        raise Exception("user not found")

    password_new = user.get("password")
    password_old = mem_user.get("password")

    if password_new != None and password_new != password_old:
        _check_password(password_new)
    
    mem_user.update(user)
    mem_user.mtime = xutils.format_time()
    if password_new != None and password_old != password_new:
        # 修改密码
        mem_user.salt = textutil.random_string(6)
        mem_user.token = gen_new_token()

    dbutil.put("user:%s" % name, mem_user)

    xutils.trace("UserUpdate", mem_user)

    refresh_users()

    # 刷新完成之后再发送消息
    xmanager.fire("user.update", dict(user_name = name))

def delete_user(name):
    if name == "admin":
        return
    name = name.lower()
    dbutil.delete("user:%s" % name)
    
    refresh_users()

def has_login_by_cookie(name = None):
    cookies = web.cookies()
    session_id = cookies.get("sid")
    session_info = get_valid_session_by_id(session_id)

    if session_info is None:
        return False

    name_in_cookie = session_info.user_name

    log_debug("has_login_by_cookie: name={}, name_in_cookie={}", name, name_in_cookie)

    user = get_user_by_name(name_in_cookie)
    if user is None:
        return False

    if user.token != session_info.token:
        return False

    if name is None:
        return True
    else:
        return name_in_cookie == name


@logutil.timeit_deco(logargs=True,logret=True,switch_func=_is_debug_enabled)
def has_login(name=None):
    """验证是否登陆
    如果``name``指定,则只能该用户名通过验证
    """
    if xconfig.IS_TEST:
        return True
    
    # 优先使用token
    user = get_user_from_token()
    if user != None:
        if name is None:
            return True
        return user.get("name") == name

    return has_login_by_cookie(name)

@logutil.timeit_deco(logargs=True,logret=True,switch_func=_is_debug_enabled)
def is_admin():
    return xconfig.IS_TEST or has_login("admin")

def check_login(user_name=None):
    if has_login(user_name):
        return
    
    if has_login():
        xutils.log("unauthorized visit, user:%s, url:%s" % (user_name, web.ctx.path))
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

def login_user_by_name(user_name, login_ip = None):
    assert user_name != None
    session_id = create_user_session(user_name, login_ip = login_ip)
    _setcookie("sid", session_id)

    # 更新最近的登录时间
    update_user(user_name, dict(login_time=xutils.format_datetime()))   

def logout_current_user():
    sid = get_session_id_from_cookie()
    delete_user_session_by_id(sid)

def is_user_exist(user_name):
    user = get_user_by_name(user_name)
    return user != None

def check_old_password(user_name, password):
    user_info = get_user_by_name(user_name)
    if user_info is None:
        raise Exception("用户不存在")
    
    if user_info.password != password:
        raise Exception("旧的密码不匹配")

def init():
    global BUILTIN_USER_DICT
    BUILTIN_USER_DICT = dict()
    _create_temp_user(BUILTIN_USER_DICT, "admin")
    _create_temp_user(BUILTIN_USER_DICT, "test")

xutils.register_func("user.get_config_dict", get_user_config_dict, "xauth")
xutils.register_func("user.get_config",      get_user_config,      "xauth")

