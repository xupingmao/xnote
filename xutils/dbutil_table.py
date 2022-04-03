# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 21:22:40
# @modified 2022/04/03 21:09:24
# @filename dbutil_table.py

from xutils.dbutil_base import *
from urllib.request import quote

register_table("_index", "通用索引")

MAX_INT = (1 << 63)-1

def dict_del(dict, key):
    if key in dict:
        del dict[key]

def encode_int(int_val):
    """把整型转换成字符串，比较性保持不变
    >>> encode_int(10) > encode_int(1)
    True
    >>> encode_int(12) == encode_int(12)
    True
    >>> encode_int(-1) > encode_int(-10)
    True
    >>> encode_int(12) > encode_int(-1)
    True
    >>> encode_int(10**5) > encode_int(1)
    True
    """
    if not isinstance(int_val, int):
        raise Exception("encode_int: expect int but see: (%r)" % int_val)
    if abs(int_val) > MAX_INT:
        raise Exception("encode_int: int value must between [-%s, %s]" % (MAX_INT, MAX_INT))
    
    # 负数需要放在前面
    # 使用64位二进制存储
    # 第一位数字表示符号，1表示正数，0表示负数，其余63位可以用于存储数字
    flag = 1 << 63
    if int_val < 0:
        int_val = MAX_INT + int_val
    else:
        int_val = int_val | flag
    
    return "%016X" % int_val

def encode_float(value):
    """把浮点数编码成字符串
    >>> encode_float(10.5) > encode_float(5.5)
    True
    >>> encode_float(10.5) > encode_float(-10.5)
    True
    >>> encode_float(-0.5) > encode_float(-1.5)
    True
    """
    if value < 0:
        value += 10**20
        return "A%020.10f" % value
    else:
        return "B%020.10f" % value

def encode_str(value):
    """编码字符串
    >>> encode_str("a:b")
    'a%58b'
    >>> encode_str("a%b")
    'a%20b'
    >>> encode_str("中文123")
    '中文123'
    """
    value = value.replace("%", "%20")
    value = value.replace(":", "%58")
    return value

def decode_str(value):
    value = value.replace("%58", ":")
    value = value.replace("%20", "%")
    return value

def encode_index_value(value):
    if value is None:
        return chr(0)
    if isinstance(value, str):
        return encode_str(value)
    if isinstance(value, int):
        return encode_int(value)
    if isinstance(value, float):
        return encode_float(value)
    raise Exception("unknown index_type:%r" % type(value))

class LdbTable:
    """基于leveldb的表，比较常见的是以下2种
    * key = prefix:record_id           全局数据库
    * key = prefix:user_name:record_id 用户维度数据

    字段说明: 
    * prefix    代表的是功能类型，比如猫和狗是两种不同的动物，锤子和手机是两种
                不同的工具
    * user_name 代表用户名，比如张三和李四，也可以是其他类型的对象ID，比如笔记ID
    * record_id 代表一条记录的ID，从属于user_name

    注: record_id建议使用全局ID，尽量避免多级主键，如果使用多级主键，移动记录会
        比较麻烦，要重新构建主键
    """

    def __init__(self, table_name, user_name = None, 
            key_name = "_key", id_name = "_id"):
        global INDEX_INFO_DICT
        # 参数检查
        check_table_name(table_name)

        self.table_name = table_name
        self.key_name = key_name
        self.id_name  = id_name
        self.prefix = table_name
        self.user_name = user_name
        self.index_names = INDEX_INFO_DICT.get(table_name) or set()

        if user_name != None:
            assert user_name != ""
            self.prefix += ":" + user_name

        if self.prefix[-1] != ":":
            self.prefix += ":"

    def define_index(self, index_key):
        # validate_str(index_key, "index_key must be str")
        # index_table = "_index$%s$%s" % (self.table_name, index_key)
        # description = "%s表索引" % self.table_name
        # register_table_inner(index_table, description)
        # self.index_names.add(index_key)
        raise Exception("deprecated: use register_table_index instead")

    def build_key(self, *argv):
        return self.prefix + self.build_key_no_prefix(*argv)

    def build_key_no_prefix(self, *argv):
        return ":".join(filter(None, argv))

    def _get_key_from_obj(self, obj):
        validate_dict(obj, "obj is not dict")
        return obj.get(self.key_name)

    def _get_id_from_obj(self, obj):
        key = self._get_key_from_obj(obj)
        return key.rsplit(":",1)[-1]

    def _get_id_from_key(self, key):
        return key.rsplit(":",1)[-1]

    def _format_value(self, key, value):
        if not isinstance(value, dict):
            value = Storage(_raw = value)

        value[self.key_name] = key
        return value

    def _get_result_from_tuple_list(self, tuple_list):
        result = []
        for key, value in tuple_list:
            value = self._format_value(key, value)
            result.append(value)
        return result

    def _convert_to_db_row(self, obj):
        obj_copy = dict(**obj)
        dict_del(obj_copy, self.key_name)
        dict_del(obj_copy, self.id_name)
        return obj_copy

    def _get_id_value(self, id_type = "uuid", id_value = None):
        if id_type == "uuid":
            validate_none(id_value, "invalid id_value")
            return xutils.create_uuid()
        elif id_type == "timeseq":
            validate_none(id_value, "invalid id_value")
            return timeseq()
        elif id_value != None:
            validate_none(id_type, "invalid id_type")
            return id_value
        else:
            raise Exception("unknown id_type:%s" % id_type)

    def _check_before_delete(self, key):
        if not key.startswith(self.prefix):
            raise Exception("invalid key:%s" % key)

    def _check_value(self, obj):
        if not isinstance(obj, dict):
            raise Exception("invalid obj:%r, expected dict" % type(obj))

    def _check_key(self, key):
        if not key.startswith(self.prefix):
            raise Exception("invalid key:(%s), prefix:(%s)" % (key, self.prefix))

    def _check_index_name(self, index_name):
        validate_str(index_name, "invalid index_name:%r" % index_name)
        if index_name not in self.index_names:
            raise Exception("invalid index_name:%r" % index_name)

    def _check_user_name(self, user_name):
        user_name = self.user_name or user_name
        info = get_table_info(self.table_name)
        if info.check_user:
            validate_str(user_name, "invalid user_name:{!r}", user_name)

    def _get_prefix(self, user_name = None):
        user_name = self.user_name or user_name
        if user_name is None:
            return self.table_name + ":"
        else:
            return self.table_name + ":" + user_name + ":"

    def _get_index_prefix(self, index_name, user_name = None):
        self._check_index_name(index_name)
        self._check_user_name(user_name)

        index_prefix = "_index$%s$%s" % (self.table_name, index_name)
        return self.build_key_no_prefix(index_prefix, self.user_name or user_name)

    def _escape_key(self, key):
        return quote(key)

    def _get_escaped_key_from_obj(self, obj):
        obj_key = self._get_key_from_obj(obj)
        return quote(obj_key)

    def _update_index(self, old_obj, new_obj, batch, user_name = None, force_update = False):
        if len(self.index_names) == 0:
            return

        validate_obj(new_obj, "invalid new_obj")

        # 插入的时候old_obj为空
        obj_id  = self._get_id_from_obj(new_obj)
        obj_key = self._get_key_from_obj(new_obj)
        validate_str(obj_id, "invalid obj_id")
        escaped_obj_id = self._escape_key(obj_id)

        for index_name in self.index_names:
            index_prefix = self._get_index_prefix(index_name, user_name = user_name)
            old_value = None
            new_value = None
            
            if old_obj != None:
                old_value = old_obj.get(index_name)

            if new_obj != None:
                new_value = new_obj.get(index_name)

            # 索引值是否变化
            index_changed = (new_value != old_value)

            if not index_changed:
                logging.debug("index value unchanged, index_name:(%s), value:(%s)", 
                    index_name, old_value)
                if not force_update:
                    continue
                # else: 强制更新

            # 只要有旧的记录，就要清空旧索引值
            if old_obj != None and index_changed:
                old_value = encode_index_value(old_value)
                batch.check_and_delete(index_prefix + ":" + old_value + ":" + escaped_obj_id)

            # 新的索引值始终更新
            new_value = encode_index_value(new_value)
            batch.check_and_put(index_prefix + ":" + new_value + ":" + escaped_obj_id, obj_key)

    def _delete_index(self, old_obj, batch, user_name = None):
        obj_id  = self._get_id_from_obj(old_obj)
        escaped_obj_id = self._escape_key(obj_id)

        for index_name in self.index_names:
            old_value = old_obj.get(index_name)
            if old_value is None:
                continue
            old_value = encode_index_value(old_value)
            index_prefix = self._get_index_prefix(index_name, user_name = user_name)
            index_key = index_prefix + ":" + old_value + ":" + escaped_obj_id
            batch.delete(index_key)

    def _put_obj(self, key, obj):
        # ~~写redo-log，启动的时候要先锁定检查redo-log，恢复异常关闭的数据~~
        # 不需要重新实现redo-log，直接用leveldb的批量处理功能即可
        # 使用leveldb的批量操作可以确保不会读到未提交的数据
        batch = create_write_batch()
        with get_write_lock(key):
            old_obj = get(key)
            self._format_value(key, obj)
            batch.put(key, self._convert_to_db_row(obj))
            self._update_index(old_obj, obj, batch)
            # 更新批量操作
            commit_write_batch(batch)

    def is_valid_key(self, key = None, user_name = None):
        if user_name is None:
            return key.startswith(self.prefix)
        else:
            return key.startswith(self.prefix + user_name)

    def get_by_id(self, row_id, default_value = None):
        validate_str(row_id, "invalid row_id:{!r}", row_id)
        key = self.build_key(row_id)
        return self.get_by_key(key, default_value)

    def get_by_key(self, key, default_value = None):
        if key == "":
            return None
        self._check_key(key)
        value = get(key, default_value)
        if value is None:
            return None

        return self._format_value(key, value)

    def insert(self, obj, id_type = "timeseq", id_value = None):
        self._check_value(obj)
        id_value = self._get_id_value(id_type, id_value)
        key  = self.build_key(id_value)

        obj[self.key_name] = key
        obj[self.id_name]  = id_value

        self._put_obj(key, obj)
        return key

    def insert_by_user(self, user_name, obj, id_type = "timeseq"):
        """不建议使用，建议初始化时设置user_name"""
        validate_str(user_name, "invalid user_name")
        self._check_value(obj)

        id_value = self._get_id_value(id_type)
        key  = self.build_key(user_name, id_value)
        self._put_obj(key, obj)
        return key

    def update(self, obj):
        """从`obj`中获取主键`key`进行更新"""
        self._check_value(obj)

        obj_key = self._get_key_from_obj(obj)
        self._check_key(obj_key)

        update_obj = self._convert_to_db_row(obj)

        self._put_obj(obj_key, update_obj)

    def update_by_id(self, id, obj, user_name = None):
        """通过ID进行更新，如果key包含用户，必须有user_name(初始化定义或者传入参数)"""
        self._check_user_name(user_name)
        key = self.build_key(user_name, id)
        self.update_by_key(key, obj)

    def update_by_key(self, key, obj):
        """直接通过`key`进行更新"""
        self._check_key(key)
        self._check_value(obj)
        
        update_obj = self._convert_to_db_row(obj)
        self._put_obj(key, update_obj)

    def rebuild_index(self, obj, user_name = None):
        self._check_value(obj)
        self._check_user_name(user_name)

        key = self._get_key_from_obj(obj)
        batch = create_write_batch()
        with get_write_lock(key):
            old_obj = get(key)
            self._format_value(key, obj)
            self._update_index(old_obj, obj, batch, 
                force_update = True, 
                user_name = user_name)
            # 更新批量操作
            commit_write_batch(batch)

    def repair_index(self):
        repair = TableIndexRepair(self)
        repair.repair_index()

    def delete(self, obj):
        obj_key = self._get_key_from_obj(obj)
        self.delete_by_key(obj_key)

    def delete_by_id(self, id):
        validate_str(id, "delete_by_id: id is not str")
        key = self.build_key(id)
        self.delete_by_key(key)

    def delete_by_key(self, key, user_name = None):
        validate_str(key, "delete_by_key: invalid key")
        self._check_before_delete(key)
        self._check_user_name(user_name)

        old_obj = get(key)
        if old_obj is None:
            return

        with get_write_lock(key):
            batch = create_write_batch()
            self._format_value(key, old_obj)
            self._delete_index(old_obj, batch)
            # 更新批量操作
            batch.delete(key)
            commit_write_batch(batch)


    def iter(self, offset = 0, limit = 20, reverse = False, key_from = None, 
            filter_func = None, fill_cache = True):
        """返回一个遍历的迭代器
        @param {int} offset 返回结果下标开始
        @param {int} limit  返回结果最大数量
        @param {bool} reverse 返回结果是否逆序
        @param {str} key_from 开始的key，这里是相对的key，也就是不包含table_name
        @param {func} filter_func 过滤函数
        """
        if key_from == "":
            key_from = None

        if key_from != None:
            key_from = self.build_key(key_from)

        for key, value in prefix_iter(self.prefix, filter_func, offset, limit, 
                reverse = reverse, include_key = True, key_from = key_from, 
                fill_cache = fill_cache):
            yield self._format_value(key, value)

    def list(self, *args, **kw):
        result = []
        for value in self.iter(*args, **kw):
            result.append(value)
        return result

    def get_first(self):
        result = self.list(limit = 1)
        if len(result) > 0:
            return result[0]
        else:
            return None

    def get_last(self):
        result = self.list(limit = 1, reverse = True)
        if len(result) > 0:
            return result[0]
        else:
            return None

    def list_by_user(self, user_name, offset = 0, limit = 20, reverse = False):
        tuple_list = prefix_list(self.prefix + user_name, None, 
            offset, limit, reverse = reverse, include_key = True)
        return self._get_result_from_tuple_list(tuple_list)

    def list_by_func(self, user_name, filter_func = None, 
            offset = 0, limit = 20, reverse = False):
        tuple_list = prefix_list(self.prefix + user_name, filter_func, 
            offset, limit, reverse = reverse, include_key = True)
        return self._get_result_from_tuple_list(tuple_list)

    def create_index_map_func(self, filter_func):
        def map_func(key, value):
            # 先判断实例是否存在
            obj = self.get_by_key(value)
            if obj is None:
                # delete(key)
                logging.warning("invalid key:(%s)", key)
                return None

            # 检查key是否匹配
            obj_id = key.rsplit(":", 1)[-1]
            key_obj_id_temp = self._get_id_from_obj(obj)
            key_obj_id = quote(key_obj_id_temp)
            if obj_id != key_obj_id:
                logging.warning("invalid obj_id:(%s), obj_id:(%s)", obj_id, key_obj_id)
                return None

            # 用于调试
            # setattr(obj, "_idx_key", key)

            if filter_func is None:
                return obj
            else:
                # 这里应该是使用obj参数来过滤
                is_match = filter_func(key, obj)
                if is_match:
                    return obj
                return None
        return map_func


    def count_by_index(self, index_name, filter_func = None, index_value = None):
        if index_value != None:
            index_value = encode_index_value(index_value)
            prefix = self._get_index_prefix(index_name) + ":" + index_value
        else:
            prefix = self._get_index_prefix(index_name)

        map_func = self.create_index_map_func(filter_func)
        return prefix_count(prefix, map_func = map_func)

    def list_by_index(self, index_name, filter_func = None, 
            offset = 0, limit = 20, reverse = False, 
            index_value = None):
        """通过索引查询结果列表
        @param {str}  index_name 索引名称
        @param {func} filter_func 过滤函数
        @param {int}  offset 开始索引
        @param {int}  limit  返回记录限制
        @param {bool} reverse 是否逆向查询
        """
        if index_value != None:
            index_value = encode_index_value(index_value)
            prefix = self._get_index_prefix(index_name) + ":" + index_value
        else:
            prefix = self._get_index_prefix(index_name)

        map_func = self.create_index_map_func(filter_func)
        return list(prefix_iter(prefix, offset = offset, limit = limit, 
            map_func = map_func,
            reverse = reverse, include_key = False))

    def count(self, filter_func = None, user_name = None):
        if filter_func is None:
            prefix = self._get_prefix(user_name = user_name)
            return count_table(prefix)
        else:
            prefix = self._get_prefix(user_name = user_name)
            return prefix_count(prefix, filter_func)

    def count_by_user(self, user_name):
        return self.count(user_name = user_name)

    def count_by_func(self, user_name, filter_func):
        assert filter_func != None, "[count_by_func.assert] filter_func != None"
        return self.count(user_name = user_name, filter_func = filter_func)


class PrefixedDb(LdbTable):
    """plyvel中叫做prefixed_db"""
    pass


class TableIndexRepair:
    """表索引修复工具，不是标准功能，所以抽象到一个新的类里面"""

    def __init__(self, db):
        self.db = db

    def repair_index(self):
        db = self.db
        for value in db.iter(limit = -1):
            db.rebuild_index(value)

        for name in db.index_names:
            self.delete_invalid_index(name)

    def do_delete(self, key):
        logging.info("Delete {%s}", key)

        if not key.startswith("_index$"):
            logging.warning("Invalid index key:(%s)", key)
            return
        delete(key)

    def delete_invalid_index(self, name):
        db = self.db
        index_prefix = db._get_index_prefix(name)
        for old_key, record_key in prefix_iter(index_prefix, include_key = True):
            record = get(record_key)
            if record is None:
                logging.debug("empty record, key:(%s), record_id:(%s)", 
                    old_key, record_key)
                self.do_delete(old_key)
                continue

            record_id   = db._get_id_from_key(record_key)
            record_id   = db._escape_key(record_id)
            index_value = getattr(record, name)
            index_value = encode_index_value(index_value)
            new_key = index_prefix + ":" + index_value + ":" + record_id

            if new_key != old_key:
                logging.debug("index dismatch, key:(%s), record_id:(%s), correct_key:(%s)", 
                    old_key, record_key, new_key)
                self.do_delete(old_key)



