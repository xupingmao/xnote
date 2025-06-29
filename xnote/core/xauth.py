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
import xutils
import warnings
import time
import datetime
import typing
import enum

from xnote.core import xtables, xconfig, xmanager
from xnote.core import xnote_event
from xutils import textutil, dbutil, fsutil, dateutil
from xutils import Storage
from xutils import logutil
from xutils import cacheutil
from xutils import six
from xutils.sqldb.utils import safe_str
from xutils import webutil
from xutils.base import BaseDataRecord

session_cache = cacheutil.PrefixedCache(prefix="session:")
user_cache = cacheutil.PrefixedCache(prefix="user:")
refresh_cache = cacheutil.PrefixedCache(prefix="session_refresh:")

DEFAULT_CACHE_EXPIRE = 60 * 5

# 用户配置
# 通过init方法完成初始化
BUILTIN_USER_DICT = None
NAME_LENGTH_MIN = 4
PASSWORD_LEN_MIN = 6
INVALID_NAMES = None
# 会话有效期(2天)
SESSION_EXPIRE = 24 * 3600 * 2
PRINT_DEBUG_LOG = False


class TestEnv:
    """用于测试的运行时环境"""
    is_admin = False
    has_login = False
    login_user_name = "test"
    
    @classmethod
    def login_admin(cls):
        cls.is_admin = True
        cls.has_login = True
        cls.login_user_name = "admin"
        
    @classmethod
    def login_user(cls, user_name=""):
        cls.is_admin = (user_name == "admin")
        cls.has_login = True
        cls.login_user_name = user_name
        
    @classmethod
    def logout(cls):
        cls.has_login = False
        cls.is_admin = False


def get_user_db():
    return UserDao._get_db()


def get_user_config_db(user_name):
    return UserConfigDao.get_db_by_name(user_name)


class UserStatusEnum(enum.Enum):
    normal = 0
    deleted = -1

class UserDO(xutils.Storage):

    def __init__(self, **kw):
        self.id = 0
        self.name = ""
        self.password = ""
        self.password_md5 = ""
        self.token = ""
        self.ctime = ""
        self.mtime = ""
        self.login_time = ""
        self.salt = ""
        self.mobile = ""
        self.status = 0
        self.update(kw)

    @property
    def user_id(self):
        return self.id

    @classmethod
    def from_dict(cls, dict_value):
        if dict_value == None:
            return None
        assert isinstance(dict_value, dict)
        result = UserDO()
        result.update(dict_value)
        result.build()
        return result
    
    @classmethod
    def from_dict_list(cls, dict_list) -> typing.List["UserDO"]:
        result = []
        for item in dict_list:
            result.append(cls.from_dict(item))
        return result

    def build(self):
        # Fix md5
        if self.password != "" and self.password_md5 == "":
            self.password_md5 = encode_password(self.password, self.salt)

    def get_status_text(self):
        if self.status == UserStatusEnum.normal.value:
            return "正常"
        if self.status == UserStatusEnum.deleted.value:
            return "删除"
        return f"未知({self.status})"
    
    @property
    def is_admin(self):
        return self.name == "admin"

class UserDao:

    @classmethod
    def init(cls):
        cls._db = xtables.get_user_table()

    @classmethod
    def _get_db(cls):
        return cls._db
    
    @classmethod
    def get_by_name(cls, name=""):
        # type: (str) -> UserDO | None
        if name is None or name == "":
            return None

        user = user_cache.get(name)
        if user == None:
            user = cls.get_user_from_db(name)
            user_cache.put(name, user, expire=DEFAULT_CACHE_EXPIRE)

        return UserDO.from_dict(user)

    @classmethod
    def get_id_by_name(cls, name=""):
        user_info = cls.get_by_name(name)
        if user_info != None:
            return user_info.id
        return 0

    @classmethod
    def get_user_from_db(cls, name=""):
        db = get_user_db()
        user_dict = db.select_first(where=dict(name=name))
        return UserDO.from_dict(user_dict)

    @classmethod
    def get_by_token(cls, token=""):
        db = get_user_db()
        user_dict = db.select_first(where=dict(token=token))
        user_info = UserDO.from_dict(user_dict)
        if user_info != None and user_info.status == UserStatusEnum.deleted.value:
            return None
        return user_info

    @classmethod
    def get_by_id(cls, user_id=0):
        db = get_user_db()
        user_dict = db.select_first(where=dict(id=user_id))
        return UserDO.from_dict(user_dict)

    @classmethod
    def get_by_mobile(cls, mobile=""):
        db = get_user_db()
        user_dict = db.select_first(where=dict(mobile=mobile))
        return UserDO.from_dict(user_dict)

    @classmethod
    def list(cls, offset=0, limit=20):
        db = get_user_db()
        return UserDO.from_dict_list(db.select(offset=offset, limit=limit))

    @classmethod
    def count(cls):
        return get_user_db().count()

    @classmethod
    def create(cls, user, fire_event=True):
        assert isinstance(user, UserDO)
        name = user.name
        assert isinstance(name, six.string_types)
        assert name != ""

        user.login_time = "1970-01-01 00:00:00"
        user.pop("id")
        db = get_user_db()
        user_id = db.insert(**user)
        #xutils.trace("UserAdd", name)
        if fire_event:
            event = Storage(user_name=name)
            xmanager.fire("user.create", event)

        assert isinstance(user_id, int)
        return user_id

    @classmethod
    def update(cls, user_info):
        assert isinstance(user_info, UserDO)
        db = get_user_db()

        if user_info.password != "":
            user_info.password_md5 = encode_password(
                user_info.password, user_info.salt)
            user_info.password = ""

        db.update(where=dict(id=user_info.id), **user_info)
        user_cache.delete(user_info.name)
        #有问题  临时加try-catch
        try:
            event = xnote_event.UserUpdateEvent()
            event.user_id = user_info.user_id
            event.user_name = user_info.name
            xutils.trace("UserUpdate", user_info)
            # 刷新完成之后再发送消息
            xmanager.fire("user.update", event)
        except:
            pass


    @classmethod
    def delete(cls, user_info: UserDO):
        db = get_user_db()
        db.update(where=dict(id=user_info.id), status=UserStatusEnum.deleted.value)

    @classmethod
    def delete_by_name(cls, name=""):
        if name == "admin":
            return
        name = name.lower()
        db = get_user_db()
        db.delete(where=dict(name=name))
        user_cache.delete(name)

    @classmethod
    def delete_by_id(cls, id=0):
        cls._db.update(where=dict(id=id), status=UserStatusEnum.deleted.value)

    @classmethod
    def batch_get_name_by_ids(cls, ids=[]):
        if len(ids) == 0:
            return {}
        db = get_user_db()
        result = db.select(what="id, name", where="id in $ids", vars=dict(ids=ids))
        dict_result = {}
        for item in result:
            dict_result[item.id] = item.name
        return dict_result
    
    @classmethod
    def get_name_by_id(cls, user_id=0):
        if user_id == 0:
            return None
        first = cls._db.select_first(what = "id, name", where = dict(id = user_id))
        if first != None:
            return first.get("name", "")
        return None

class UserModel(UserDao):
    pass


class SessionInfo(BaseDataRecord):
    def __init__(self) -> None:
        self.user_name = ""
        self.user_id = 0
        self.sid = ""
        self.token = ""
        self.expire_time = xtables.DEFAULT_DATETIME
        self.login_ip = ""
        self.login_time = xtables.DEFAULT_DATETIME
        self.mobile = ""

    def to_save_dict(self):
        result = dict(**self)
        result.pop("id", None)
        return result

    @property
    def is_expired(self):
        now = datetime.datetime.now()
        expire_time = dateutil.to_py_datetime(self.expire_time)
        return expire_time < now

    def need_refresh(self):
        now = datetime.datetime.now()
        login_time = dateutil.to_py_datetime(self.login_time)
        return now - login_time > datetime.timedelta(days=1)


class SessionDao:

    @classmethod
    def init(cls):
        cls.db = xtables.get_table_by_name("user_session")

    @classmethod
    def get_by_sid(cls, sid=""):
        if sid == None or sid == "":
            return None
        record = session_cache.get(sid)
        if record == None:
            record = cls.db.select_first(where=dict(sid=sid))
            if record != None:
                session_cache.put(sid, record, expire=DEFAULT_CACHE_EXPIRE)

        if record == None or session_cache.is_empty(record):
            return None

        session_info = SessionInfo.from_dict(record)
        if session_info.user_name is None:
            delete_user_session_by_id(sid)
            return None

        if session_info.is_expired:
            delete_user_session_by_id(sid)
            return None

        return session_info

    @classmethod
    def create(cls, session_info: SessionInfo):
        assert isinstance(session_info, SessionInfo)
        save_dict = session_info.to_save_dict()
        new_id = cls.db.insert(**save_dict)
        session_cache.delete(session_info.sid)
        return new_id

    @classmethod
    def list_by_user_name(cls, user_name=""):
        user_id = UserDao.get_id_by_name(user_name)
        records = cls.db.select(where=dict(user_id=user_id))
        return SessionInfo.from_dict_list(records)

    @classmethod
    def delete_by_sid(cls, sid=""):
        cls.db.delete(where=dict(sid=sid))
        session_cache.delete(sid)

class SessionModel(SessionDao):
    pass

def _is_debug_enabled():
    return PRINT_DEBUG_LOG


def log_debug(fmt:str, *args):
    if PRINT_DEBUG_LOG:
        print("[xauth]", fmt.format(*args))


def is_valid_username(name: str):
    """有效的用户名为字母+数字"""
    assert INVALID_NAMES != None
    if name in INVALID_NAMES:
        return False
    if len(name) < NAME_LENGTH_MIN:
        return False

    for c in name:
        if c.isalnum() or c in "_-":
            continue
        return False
    return True


def validate_password_error(password: str):
    if len(password) < PASSWORD_LEN_MIN:
        return "密码不能少于6位"
    return None


def _create_temp_user(user_name):
    user_info = UserModel.get_by_name(user_name)
    if user_info == None:
        create_user(user_name, "123456", fire_event=False,
                    check_username=False)

    upload_dirname = xconfig.get_upload_dir(user_name)
    fsutil.makedirs(upload_dirname)


def _get_users(force_reload=False):
    """获取用户，内部接口"""
    warnings.warn("_get_users(查询所有用户)已经过时，请停止使用", DeprecationWarning)
    raise Exception("_get_users已经废弃")


def _setcookie(key, value, expires=SESSION_EXPIRE):
    # 默认保留两天,但是只要保持登录会自动刷新
    assert isinstance(key, str)
    assert isinstance(value, str)
    if xconfig.IS_TEST:
        return
    web.setcookie(key, value, expires) # type: ignore


def get_users():
    """获取所有用户，返回一个深度拷贝版本"""
    warnings.warn("get_users已经过时，请停止使用", DeprecationWarning)
    return copy.deepcopy(_get_users())


def iter_user(limit=20):
    db = get_user_db()
    if limit < 0:
        for batch in db.iter_batch():
            for item in batch:
                yield UserDO(**item)
    else:
        for user_info in db.select(limit=limit):
            yield UserDO(**user_info)


def count_user():
    db = get_user_db()
    return db.count()


def refresh_users():
    xutils.trace("ReLoadUsers", "reload users")


def get_user(name):
    warnings.warn("get_user已经过时，请使用 get_user_by_name", DeprecationWarning)
    return find_by_name(name)


def get_user_by_name(user_name):
    return UserDao.get_by_name(user_name)

def get_valid_session_by_id(sid):
    return SessionDao.get_by_sid(sid)


def list_user_session_detail(user_name):
    return SessionDao.list_by_user_name(user_name)


def create_user_session(user_name:str, expires=SESSION_EXPIRE, login_ip=""):
    # type: (str, int, str) -> SessionInfo
    user_detail = get_user_by_name(user_name)
    if user_detail is None:
        raise Exception("user not found: %s" % user_name)
    return create_session_by_user(user_detail, expires, login_ip)


def create_session_by_user(user_detail, expires=SESSION_EXPIRE, login_ip=""):
    assert isinstance(user_detail, UserDO)
    user_name = user_detail.name

    session_id = textutil.create_uuid()
    session_list = list_user_session_detail(user_name)
    session_list.sort(key=lambda x: x.expire_time)

    if len(session_list) > xconfig.WebConfig.auth_max_session_size:
        # 踢出最早的登录
        for old_session in session_list[0:2]:
            delete_user_session_by_id(old_session.sid)

    # 保存会话信息
    session_info = SessionInfo()
    session_info.user_name = user_name
    session_info.user_id = user_detail.id
    session_info.sid = session_id
    session_info.token = user_detail.token
    session_info.login_time = dateutil.format_datetime()
    session_info.login_ip = login_ip
    session_info.expire_time = dateutil.format_datetime(time.time() + expires)
    if user_detail.mobile != None and user_detail.mobile != "":
        session_info.mobile = user_detail.mobile[0:3]+"********"
    else :
        session_info.mobile = ""

    SessionDao.create(session_info)

    return session_info


def delete_user_session_by_id(sid):
    # 登录的时候会自动清理无效的sid关系
    SessionDao.delete_by_sid(sid)


def find_by_name(name):
    return UserModel.get_by_name(name)


class UserConfigDao:

    USER_CONFIG_PROP = {}  # type: dict

    @classmethod
    def init(cls):
        user_config = xconfig.load_user_config_properties()
        # 检查配置项的有效性
        for key in user_config:
            if "." in key:
                raise Exception(f"无效的用户配置项:({key}),不能包含(.),请使用(_)")
        cls.USER_CONFIG_PROP = user_config

    @classmethod
    def get_db_by_name(cls, user_name: str):
        assert user_name != None
        assert user_name != ""
        return dbutil.get_hash_table("user_config", user_name=user_name)
    
    @classmethod
    def check_config_key(cls, key: str):
        if key not in cls.USER_CONFIG_PROP:
            raise Exception(f"invalid user config: {key}")

@cacheutil.cache_deco(prefix="user_config_dict", expire=600)
def get_user_config_dict(name):
    if name is None or name == "":
        return Storage(**UserConfigDao.USER_CONFIG_PROP)

    db = get_user_config_db(name)
    config_dict = Storage(**UserConfigDao.USER_CONFIG_PROP)

    db_records = db.dict(limit=-1)
    if len(db_records) > 0:
        config_dict.update(db_records)
        return config_dict

    return Storage(**UserConfigDao.USER_CONFIG_PROP)


def get_user_config_valid_keys():
    return UserConfigDao.USER_CONFIG_PROP.keys()


def check_user_config_key(key):
    return UserConfigDao.check_config_key(key)


def get_user_config(user_name, config_key, default_value=None):
    default_value = UserConfigDao.USER_CONFIG_PROP.get(config_key)
    config_dict = get_user_config_dict(user_name)
    if config_dict is None:
        return default_value
    return config_dict.get(config_key, default_value)


@logutil.log_deco("update_user_config", log_args=True)
def update_user_config(user_name, key, value):
    check_user_config_key(key)

    db = get_user_config_db(user_name)
    result = db.put(key, value)
    cacheutil.delete(prefix="user_config_dict", args=(user_name,))
    return result


def update_user_config_dict(name, config_dict):
    assert isinstance(config_dict, dict)
    user = UserDao.get_by_name(name)
    if user is None:
        return

    for key in config_dict:
        check_user_config_key(key)

    db = get_user_config_db(name)

    for key in config_dict:
        value = config_dict.get(key)
        db.put(key, value)

    cacheutil.delete(prefix="user_config_dict", args=(name, ))


def get_user_from_token():
    token = xutils.get_argument_str("token")
    if token != None and token != "":
        return UserModel.get_by_token(token)

    sid = xutils.get_argument_str("__sid")
    if sid != "":
        return get_user_by_sid(sid)


def get_user_password(name):
    # TODO webdav需要用到密码
    user = get_user_by_name(name)
    if user != None:
        return user.password
    raise Exception("user not found")


def get_user_password_md5(user_name, use_salt=True):
    user = UserDao.get_by_name(user_name)
    assert user != None
    password = user.password
    salt = user.salt

    if use_salt:
        return encode_password(password, salt)
    else:
        return encode_password(password, None)


def get_session_id_from_cookie():
    cookies = web.cookies()
    return cookies.get("sid", "")


def get_user_from_cookie():
    sid = get_session_id_from_cookie()
    return get_user_by_sid(sid)


def get_user_by_sid(session_id=""):
    if session_id == None or session_id == "":
        return None
    session_info = get_valid_session_by_id(session_id)

    if session_info is None:
        return None

    log_debug("get_user_from_cookie: sid={}, session_info={}",
              session_id, session_info)

    return get_user_by_name(session_info.user_name)


def get_current_user():
    if TestEnv.has_login:
        return get_user_by_name(TestEnv.login_user_name)

    user = get_user_from_token()
    if user != None:
        return user

    if not hasattr(web.ctx, "env"):
        # 尚未完成初始化
        return None

    return get_user_from_cookie()


def current_user():
    return get_current_user()

def current_user_id():
    user = get_current_user()
    if user != None:
        return user.user_id
    return 0

def get_current_name():
    """获取当前用户名"""
    user = get_current_user()
    if user is None:
        return None
    return user.name


def current_name():
    return get_current_name()


def current_name_str() -> str:
    name = get_current_name()
    if name == None:
        name = "public"
    assert isinstance(name, str)
    return name


def get_current_role():
    """获取当前用户的角色"""
    user = get_current_user()
    if user is None:
        return None
    name = user.name
    if name == "admin":
        return "admin"
    else:
        return "user"

def current_role():
    return get_current_role()


def get_md5_hex(pswd: str):
    pswd_md5 = hashlib.md5()
    pswd_md5.update(pswd.encode("utf-8"))
    return pswd_md5.hexdigest()


def encode_password(password, salt: typing.Optional[str]):
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
    session_id = create_user_session(user_name).sid
    _setcookie("sid", session_id, expires=24*3600*30)


def get_user_cookie(name):
    session_list = list_user_session_detail(name)

    if len(session_list) == 0:
        sid = create_user_session(name, login_ip="system").sid
    else:
        sid = session_list[0].sid

    return "sid=%s" % sid


def gen_new_token():
    import uuid
    return uuid.uuid4().hex


def create_quick_user():
    """创建快速用户，用于第三方授权登录"""
    num_length = 5
    for i in range(10):
        name = "u" + xutils.random_number_str(num_length)
        with dbutil.get_write_lock(name):
            if UserDao.get_by_name(name) != None:
                num_length += 1
                continue
            password = xutils.create_uuid()
            new_user = UserDO()
            new_user.name = name
            new_user.password = password
            new_user.ctime = xutils.format_time()
            new_user.mtime = xutils.format_time()
            new_user.token = gen_new_token()
            new_user.salt = textutil.random_string(6)
            user_id = UserDao.create(new_user)
            return UserDao.get_by_id(user_id)
    raise Exception("create user name conflict")


def create_user(name:str, password:str, fire_event=True, check_username=True):
    if name == "" or name == None:
        return webutil.FailedResult(code="PARAM_ERROR", message="name为空")
    if password == "" or password == None:
        return webutil.FailedResult(code="PARAM_ERROR", message="password为空")
    if check_username and not is_valid_username(name):
        return webutil.FailedResult(code="INVALID_NAME", message="非法的用户名")

    name = name.lower()
    found = find_by_name(name)
    if found is not None:
        return webutil.FailedResult(code="fail", message="用户已存在")
    else:
        user = UserDO()
        user.name = name
        user.password = password
        user.salt = textutil.random_string(6)
        user.token = gen_new_token()
        user.ctime = xutils.format_time()
        user.mtime = xutils.format_time()
        user.build()

        UserModel.create(user, fire_event=fire_event)
        return webutil.SuccessResult(message="create success")


def _check_password(password):
    error = validate_password_error(password)
    if error != None:
        raise Exception(error)


def update_user(name:str, update_dict:dict):
    if name == "" or name == None:
        return
    name = name.lower()

    user_info = find_by_name(name)
    if user_info is None:
        raise Exception("user not found")

    password_new = update_dict.get("password")
    md5_new = None
    md5_old = user_info.password_md5
    if password_new != None:
        md5_new = encode_password(password_new, user_info.salt)

    if md5_new != None and md5_new != md5_old:
        # 修改密码
        _check_password(password_new)
        user_info.salt = textutil.random_string(6)
        user_info.token = gen_new_token()

    user_info.update(update_dict)
    user_info.mtime = xutils.format_time()
    UserDao.update(user_info)


def delete_user(name):
    return UserModel.delete_by_name(name)


def has_login_by_cookie(name=None):
    cookies = web.cookies()
    session_id = cookies.get("sid")
    return has_login_by_sid(name, session_id)

def has_login_by_sid(name: typing.Optional[str], session_id):
    session_info = get_valid_session_by_id(session_id)

    if session_info is None:
        return False

    name_in_cookie = session_info.user_name

    log_debug("has_login_by_cookie: name={}, name_in_cookie={}",
              name, name_in_cookie)

    user = get_user_by_name(name_in_cookie)
    if user is None:
        return False
    
    if user.status == UserStatusEnum.deleted.value:
        return False

    if user.token != session_info.token:
        return False

    if name is None:
        return True
    else:
        has_login = (name_in_cookie == name)
        if has_login and session_info.need_refresh():
            refresh_user_session(session_info)
        return has_login


def refresh_user_session(session_info: SessionInfo):
    cache_key = str(session_info.user_id)
    cache = refresh_cache.get(cache_key)
    if cache:
        return session_info
    
    login_ip = webutil.get_real_ip()
    new_session = login_user_by_name(session_info.user_name, login_ip=login_ip)
    op_log = UserOpLog()
    op_log.user_id = session_info.user_id
    op_log.type = UserOpTypeEnum.refresh_session.value
    op_log.ip = login_ip
    op_log.detail = "刷新登录态成功"
    UserOpLogDao.create_op_log(op_log)

    refresh_cache.put(cache_key, 1, expire=60*5)
    return new_session


@logutil.timeit_deco(logargs=True, logret=True, switch_func=_is_debug_enabled)
def has_login(name=None):
    """验证是否登陆
    如果``name``指定,则只能该用户名通过验证
    """
    if TestEnv.has_login:
        if name == "admin":
            return TestEnv.is_admin
        return True

    # 优先使用token
    user = get_user_from_token()
    if user != None:
        if name is None:
            return True
        return user.name == name

    return has_login_by_cookie(name)


@logutil.timeit_deco(logargs=True, logret=True, switch_func=_is_debug_enabled)
def is_admin():
    return TestEnv.is_admin or has_login("admin")


def check_login(user_name=None):
    if has_login(user_name):
        return

    if has_login():
        xutils.log("unauthorized visit, user:%s, url:%s" %
                   (user_name, web.ctx.path))
        raise web.seeother("/unauthorized")

    # 跳转到登陆URL
    redirect_to_login()


def redirect_to_login():
    path = web.ctx.fullpath
    raise web.seeother(xconfig.WebConfig.login_url + xutils.encode_uri_component(path))


def login_required(user_name=None):
    """用户登录验证装饰器"""
    def deco(func):
        def handle(*args, **kw):
            check_login(user_name)
            ret = func(*args, **kw)
            return ret
        return handle
    return deco

def admin_required():
    """管理员登录验证装饰器"""
    return login_required("admin")

def get_user_data_dir(user_name, mkdirs=False):
    fpath = os.path.join(xconfig.DATA_DIR, "files", user_name)
    if mkdirs:
        fsutil.makedirs(fpath)
    return fpath


def login_user_by_name(user_name: str, login_ip="", write_cookie=True):
    assert user_name != None
    user_info = UserDao.get_by_name(user_name)
    if user_info == None:
        raise Exception("用户不存在")
    
    if user_info.status == UserStatusEnum.deleted.value:
        raise Exception("用户已注销")

    session_info = create_session_by_user(user_info, login_ip=login_ip)
    session_id = session_info.sid
    if write_cookie:
        _setcookie("sid", session_id)

    # 更新最近的登录时间
    update_kw = dict(login_time=xutils.format_datetime())
    if user_info.password_md5 == "":
        update_kw["password"] = user_info.password

    update_user(user_name, update_kw)
    return session_info


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

    if user_info.password_md5 != encode_password(password, user_info.salt):
        raise Exception("旧的密码不匹配")

class UserOpTypeEnum(enum.Enum):
    # 登录
    login = "login"
    
    # 修改密码
    change_password = "change_password"

    # 管理员重置密码
    reset_password = "reset_password"

    # 刷新会话
    refresh_session = "refresh_session"

class UserOpLog(Storage):

    def __init__(self):
        self.ctime = dateutil.format_datetime()
        self.user_id = 0
        self.type = ""
        self.detail = ""
        self.ip = ""

    @classmethod
    def from_dict_list(cls, dict_list: list) -> typing.List["UserOpLog"]:
        result = []
        for item in dict_list:
            op_log = UserOpLog()
            op_log.update(item)
            result.append(op_log)
        return result

class UserOpLogDao:

    @classmethod
    def init(cls):
        cls.db = xtables.get_table_by_name("user_op_log")
        cls.max_log_size = 500
        cls.log_buf_size = 20

    @classmethod
    def create_op_log(cls, op_log: UserOpLog):
        assert isinstance(op_log, UserOpLog)
        assert op_log.user_id != 0
        assert op_log.ctime != ""
        assert op_log.type != ""
        assert op_log.detail != ""
        assert cls.log_buf_size > 0
        
        op_log.ip = safe_str(op_log.ip)
        
        cls.db.insert(**op_log)
        if cls.db.count(where=dict(user_id=op_log.user_id)) >= cls.max_log_size + cls.log_buf_size:
            ids = []
            for item in cls.db.select(where=dict(user_id=op_log.user_id), limit=cls.log_buf_size, order="ctime"):
                ids.append(item.id)
            if len(ids) > 0:
                cls.db.delete(where="id in $ids", vars=dict(ids=ids))

    @classmethod
    def list_by_user(cls, user_id=0, offset=0, limit=20, reverse=True):
        order = "ctime desc"
        if not reverse:
            order = "ctime"
        result_list = cls.db.select(where=dict(user_id=user_id), offset=offset, limit=limit, order=order)
        return UserOpLog.from_dict_list(result_list)
    
    @classmethod
    def count(cls, user_id=0):
        return cls.db.count(where=dict(user_id=user_id))
    
def init():
    global INVALID_NAMES

    INVALID_NAMES = xconfig.load_invalid_names()
    UserDao.init()
    UserConfigDao.init()
    SessionDao.init()
    UserOpLogDao.init()

    _create_temp_user("admin")
    _create_temp_user("test")

xutils.register_func("user.get_config_dict", get_user_config_dict, "xauth")
xutils.register_func("user.get_config",      get_user_config,      "xauth")
