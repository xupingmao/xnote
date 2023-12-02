# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-02-12 18:13:41
@LastEditors  : xupingmao
@LastEditTime : 2023-12-02 18:20:42
@FilePath     : /xnote/handlers/system/system_sync/node_follower.py
@Description  : 从节点管理
"""

import time
import logging
from xnote.core import xconfig, xtables

from xutils import Storage
from xutils import textutil, cacheutil
from xutils import dbutil, six
import xutils
from xutils.db.binlog import BinLog, FileLog, BinLogOpType
from .node_base import NodeManagerBase
from .node_base import convert_follower_dict_to_list
from .node_base import CONFIG
from .system_sync_proxy import HttpClient, empty_http_client
from .models import FileIndexInfo, LeaderStat
from xutils.mem_util import log_mem_info_deco

fs_sync_index_db = dbutil.get_hash_table("fs_sync_index")


def filter_result(result, offset):
    data = []
    for item in result.data:
        if item.get("_id", "") == offset:
            logging.debug("跳过offset:%s", offset)
            continue
        data.append(item)

    result.data = data
    return result

class Follower(NodeManagerBase):

    # PING的时间间隔，单位是秒
    # Leader侧的失效时间是1小时
    PING_INTERVAL = 600

    def __init__(self):
        self.follower_list = []
        self.leader_info = None
        self.ping_error = None
        self.ping_result = None
        self.admin_token = None
        self.last_ping_time = -1
        self.fs_index_count = -1
        # 同步完成的时间
        self.fs_sync_done_time = -1
        self._debug = False
        self.http_client = self.get_client()
        self.file_syncer = FileSyncer(self.http_client)
        self.db_syncer = DBSyncer(file_syncer = self.file_syncer)

    def create_http_client(self):
        leader_host = self.get_leader_url()
        leader_token = self.get_leader_token()
        return HttpClient(leader_host, leader_token, self.admin_token)

    def get_client(self):
        return self.create_http_client()

    def get_node_id(self):
        return xconfig.get_global_config("system.node_id", "unknown_node_id")

    def get_leader_node_id(self):
        if self.leader_info != None:
            return self.leader_info.get("node_id")
        return "<unknown>"

    def get_current_port(self):
        return xconfig.get_global_config("system.port")
    
    def is_token_active(self):
        now = time.time()
        is_active = (now - self.last_ping_time) < self.PING_INTERVAL
        return self.admin_token != None and is_active

    def ping_leader(self, force=True):
        if self.is_token_active() and not force:
            return self.ping_result
        
        return self.do_ping_leader()

    def do_ping_leader(self):
        port = self.get_current_port()

        fs_sync_offset = str(self.get_fs_sync_last_id())

        leader_host = self.get_leader_url()
        if leader_host != None:
            client = self.get_client()
            params = dict(port=port, fs_sync_offset=fs_sync_offset,
                          node_id=self.get_node_id())
            result_obj = client.get_stat(params)

            self.update_ping_result(result_obj)
            return result_obj

        return None

    def update_ping_result(self, result0):
        if result0 is None:
            logging.error("PING主节点:返回None")
            return

        result = LeaderStat(**result0)
        if result.code != "success":
            self.ping_error = result.message
            logging.error("PING主节点失败:%s", self.ping_error)
            return

        logging.debug("PING主节点成功")

        self.ping_error = None
        self.ping_result = result
        follower_dict = result.get("follower_dict", {})
        self.follower_list = convert_follower_dict_to_list(follower_dict)
        self.leader_info = result.get("leader")
        self.last_ping_time = time.time()

        if len(self.follower_list) > 0:
            item = self.follower_list[0]
            self.admin_token = item.admin_token
            self.fs_index_count = item.fs_index_count
            self.http_client.admin_token = self.admin_token

    def get_follower_list(self):
        return self.follower_list

    @cacheutil.cache_deco("sync.leader_host")
    def get_leader_url(self):
        return CONFIG.get("leader.host")
    
    def get_leader_info(self):
        if self.ping_result != None:
            return self.ping_result.get("leader")
        return None

    def get_ping_error(self):
        return self.ping_error

    def need_sync(self):
        if self.fs_sync_done_time < 0:
            return True

        last_sync = time.time() - self.fs_sync_done_time
        return last_sync >= self.PING_INTERVAL

    def get_fs_sync_last_id(self):
        value = CONFIG.get("fs_sync_last_id")
        try:
            return int(value)
        except:
            return 0
        
    def sync_file_step(self):
        client = self.get_client()
        # 先重试失败的任务
        client.retry_failed()
    
        last_id = self.get_fs_sync_last_id()
        
        logging.debug("fs_sync_last_id=%s", last_id)
        result = client.list_files(last_id)
        logging.debug("list files result=(%s), last_id=(%s)", result, last_id)

        if result is None:
            logging.error("返回结果为空")
            return []

        data = result.get("data", [])
        assert isinstance(data, list)
        
        if len(data) == 0:
            logging.debug("返回文件列表为空")
            self.fs_sync_done_time = time.time()
            return data
        
        for item in data:
            item = FileIndexInfo(**item)
            last_id = max(last_id, item.id)

        # logging.debug("result:%s", result)
        client.download_files(result)

        # offset可能不变
        logging.debug("result.sync_offset:%s", result.sync_offset)
        logging.debug("last_id = %s", last_id)

        CONFIG.put("fs_sync_last_id", last_id)
        return data

    def sync_files_from_leader(self):
        result = self.ping_leader()
        if result == None:
            logging.error("ping_leader结果为空")
            return

        if not self.need_sync():
            # logging.debug("没到SYNC时间")
            return

        has_next = True
        loop_count = 0
        while has_next and loop_count < 100:
            result = self.sync_file_step()
            has_next = len(result) > 0
            loop_count += 1

        return result

    def get_sync_process(self):
        if self.fs_index_count < 0:
            return "-1"

        count = self.count_sync_done()
        if count == 0:
            return "0%"
        return "%.2f%%" % (count / self.fs_index_count * 100.0)

    def sync_for_home_page(self):
        return self.ping_leader() != None

    def get_fs_index_count(self):
        return self.fs_index_count

    def count_sync_done(self):
        return dbutil.count_table("fs_sync_index_copy")

    def count_sync_failed(self):
        return dbutil.count_table("fs_sync_index_failed")

    def reset_sync(self):
        CONFIG.put("fs_sync_offset", "")
        CONFIG.put("db_sync_offset", "")
        CONFIG.put("follower_db_sync_state", "full")
        CONFIG.delete("follower_binlog_last_seq")
        CONFIG.delete("follower_db_last_key")
        self.fs_sync_done_time = -1

        db = dbutil.get_hash_table("fs_sync_index_copy")
        for key, value in db.iter(limit=-1):
            db.delete(key)

    def sync_db_from_leader(self):
        leader_host = self.get_leader_url()
        if leader_host == None:
            logging.debug("leader_host为空")
            raise Exception("leader_host为空")

        ping_result = self.ping_leader()
        if ping_result == None:
            logging.debug("ping_leader结果为空")
            raise Exception("ping_leader结果为空")

        leader_token = self.get_leader_token()
        if leader_token == "":
            logging.debug("leader_token为空")
            raise Exception("leader_token为空")
        
        self.db_syncer.sync_db(self.get_client())
    
    def is_at_full_sync(self):
        return self.db_syncer.get_db_sync_state() == "full"


class FileSyncer:
    """文件同步器"""
    def __init__(self, http_client = empty_http_client):
        self.http_client = http_client

    def handle_file_binlog(self, key, value):
        if value == None:
            logging.warning("value is None, key=%s", key)
            return
        self.sync_file(value)
    
    def sync_file(self, item):
        new_item = FileIndexInfo(**item)
        self.http_client.download_file(new_item)

empty_file_syncer = FileSyncer()

class DBSyncer:

    MAX_LOOPS = 1000 # 最大循环次数
    FULL_SYNC_MAX_LOOPS = 10000 # 全量同步最大循环次数

    def __init__(self, *, debug = True, file_syncer = empty_file_syncer):
        self._binlog = BinLog.get_instance()
        self.debug = debug
        self.file_syncer = file_syncer
    
    def get_table_by_key(self, key):
        table_name = key.split(":")[0]
        if dbutil.TableInfo.is_registered(table_name):
            return dbutil.get_table(table_name)
        return None
    
    def get_table_name_by_key(self, key):
        return key.split(":")[0]
    
    def get_binlog_last_seq(self):
        value = CONFIG.get("follower_binlog_last_seq", 0)
        if isinstance(value, int):
            return value
        return 0

    def put_binlog_last_seq(self, last_seq):
        return CONFIG.put("follower_binlog_last_seq", last_seq)

    def get_db_sync_state(self):
        return CONFIG.get("follower_db_sync_state", "full")

    def put_db_sync_state(self, state):
        assert state in ("full", "binlog")
        CONFIG.put("follower_db_sync_state", state)
    
    def get_db_last_key(self):
        # type: () -> str
        # 全量同步使用，按照key进行遍历
        value = CONFIG.get("follower_db_last_key", "")
        assert isinstance(value, six.string_types)
        return value

    def put_db_last_key(self, last_key):
        CONFIG.put("follower_db_last_key", last_key)

    def get_table_v2_or_None(self, table_name):
        try:
            return dbutil.get_table_v2(table_name)
        except:
            return None
    
    def put_and_log(self, key, value):
        assert key != None
        assert value != None
        done = False
        try:
            table_name = self.get_table_name_by_key(key)
            table_v2 = self.get_table_v2_or_None(table_name)
            if table_v2 != None:
                table_v2.put_by_key(key, value, fix_index=True)
                return
            
            table_info = dbutil.get_table_info(table_name)
            if table_info == None:
                logging.warning("table not exists: %s", table_name)
                return
            
            if table_info.type == "hash":
                dbutil.put(key, value)
                done = True
            else:
                table = dbutil.get_table(table_name)
                table.update_by_key(key, value)
                done = True
        except:
            xutils.print_exc()
        
        if not done:
            # 失败才记录binlog
            batch = dbutil.create_write_batch()
            batch.put(key, value, check_table=False)
            self._binlog.add_log("put", key, value, batch = batch)
            batch.commit()
    
    def delete_and_log(self, key):
        assert key != None
        done = False
        try:
            table_name = self.get_table_name_by_key(key)
            table_v2 = self.get_table_v2_or_None(table_name)
            if table_v2 != None:
                table_v2.delete_by_key(key)
                return
            
            table = self.get_table_by_key(key)
            if table != None:
                table.delete_by_key(key)
                done = True
        except:
            logging.error("key=%s", key)
            xutils.print_exc()

        if not done:
            batch = dbutil.create_write_batch()
            batch.delete(key)
            self._binlog.add_log("delete", key, None, batch = batch)
            batch.commit()
    
    @log_mem_info_deco("follower.sync_db")
    def sync_db(self, proxy):
        sync_state = self.get_db_sync_state()
        if sync_state == "binlog":
            # 增量同步
            self.sync_by_binlog(proxy)
        else:
            # 全量同步
            self.sync_db_full(proxy)

    def sync_db_full(self, proxy):
        steps = 0
        while steps < self.FULL_SYNC_MAX_LOOPS:
            last_key = self.get_db_last_key()
            count = self.sync_db_full_step(proxy, last_key)
            if count == 0:
                break
            steps+=1

    def sync_db_full_step(self, proxy, last_key):
        # type: (HttpClient, str) -> int
        result = proxy.list_db(last_key)

        if self.debug:
            logging.debug("-------------\nresp:%s\n\n", result)

        result_obj = textutil.parse_json(result)
        assert isinstance(result_obj, dict)
        count = self.sync_db_by_result(result_obj, last_key)
        return count

    @log_mem_info_deco("sync_by_binlog")
    def sync_by_binlog(self, proxy): # type: (HttpClient) -> object
        has_next = True
        loops = 0
        last_seq = ""

        while has_next:
            loops += 1
            if loops > self.MAX_LOOPS:
                logging.error("too deep loops, last_seq=%s", last_seq)
                raise Exception("too deep loops")

            last_seq = self.get_binlog_last_seq()
            result_obj = proxy.list_binlog(last_seq)
            
            if self.debug:
                logging.debug("list binlog result=%s" % result_obj)

            code = result_obj.get("code")
            data = result_obj.get("data")
            # TODO 优化has_next判断
            has_next = (data != None and len(data) > 1)
            logging.info("code=%s, has_next=%s", code, has_next)

            if code == "success":
                self.sync_by_binlog_step(result_obj)
            elif code == "sync_broken":
                logging.error("同步binlog异常, 重新全量同步...")
                self.put_binlog_last_seq(0)
                self.put_db_sync_state("full")
                self.put_db_last_key("")
                self.sync_db_full(proxy)
                return "sync_by_full"
            else:
                raise Exception("未知的code:%s" % code)
        
        return None

    @log_mem_info_deco("sync_by_binlog_step")
    def sync_by_binlog_step(self, result_obj):
        last_seq = self.get_binlog_last_seq()
        max_seq = last_seq
        data_list = result_obj.get("data")
        for data in data_list:
            seq = data.get("seq")
            assert isinstance(seq, int)

            if seq == last_seq:
                continue

            optype = data.get("optype")
            key = data.get("key")
            value = data.get("value")

            if optype in (BinLogOpType.put, BinLogOpType.delete):
                self.handle_kv_binlog(data)
            elif optype == "file_upload":
                self.file_syncer.handle_file_binlog(key, value)
            elif optype == "file_rename":
                # TODO 重命名需要考虑删除原来的文件
                self.file_syncer.handle_file_binlog(key, value)
            elif optype == "file_delete":
                # TODO 考虑移动到一个删除文件夹下面
                logging.info("【不处理】删除文件操作: %s", data)
            elif optype in (BinLogOpType.sql_upsert, BinLogOpType.sql_delete):
                self.handle_sql_binlog(data)
            else:
                logging.error("未知的optype:%s", optype)

            max_seq = max(max_seq, seq)
        if max_seq != last_seq:
            self.put_binlog_last_seq(max_seq)
        else:
            logging.info("db已经保持同步")
    
    def handle_kv_binlog(self, data):
        key = data.get("key")
        value = data.get("value")
        assert key != None
        if value == None:
            self.delete_and_log(key)
        else:
            self.put_and_log(key, value)

    def handle_sql_binlog(self, data):
        optype = data.get("optype")
        table_name = data.get("table_name")
        value = data.get("value")
        pk_value = data.get("key")

        if table_name == None:
            return
        
        if not xtables.is_table_exists(table_name):
            logging.info("表不存在, table_name=%s", table_name)
            return
        
        table = xtables.get_table_by_name(table_name)
        pk_name = table.table_info.pk_name
        where = {pk_name:pk_value}
        if optype == BinLogOpType.sql_delete:
            table.delete(where=where)

        if optype == BinLogOpType.sql_upsert:
            old = table.select_first(where=where)
            value = table.filter_record(value)
            # TODO 使用replace解决冲突的问题?
            try:
                if old == None:
                    table.insert(**value)
                else:
                    table.update(where=where, **value)
            except Exception as err:
                xutils.print_exc()
                print(f"error value={value}")
                self.ignore_or_raise(err)
                
    def ignore_or_raise(self, err: Exception):
        err_msg = str(err)
        print(f"err_msg={err_msg}")
        err_msg = err_msg.lower()
        if err_msg.startswith("(1292, \"incorrect datetime value"):
            # mysql: datetime异常,无法执行成功
            return
        if err_msg.startswith("(1062, \"duplicate entry"):
            # mysql: 主键冲突
            return
        if err_msg.startswith("(1366, \"incorrect integer value:"):
            # mysql: 类型错误
            return
        if err_msg.startswith("unique constraint failed:"):
            # sqlite: 主键冲突
            return
        raise err

    def sync_db_by_result(self, result_obj: dict, last_key):
        # type: (dict, str) -> int
        code = result_obj.get("code")
        count = 0
        assert code == "success"
        data = result_obj.get("data")
        assert data != None, "data不能为空"
        if last_key == "":
            # 这里需要保存一下位点，后面增量同步从这里开始
            binlog_last_seq = data.get("binlog_last_seq")
            assert isinstance(binlog_last_seq, int)
            self.put_binlog_last_seq(binlog_last_seq)

        rows = data.get("rows")
        if not isinstance(rows, list):
            logging.error("resp:%s", result_obj)
            raise Exception("data.rows必须为list,当前类型(%s)" % type(rows))

        new_last_key = last_key
        for row in rows:
            key = row.get("key")
            value = row.get("value")
            assert key != None
            assert value != None
            if key == last_key:
                continue
            
            self.put_and_log(key, value)
            new_last_key = key
            count += 1

        if count == 0:
            self.put_db_sync_state("binlog")
        else:
            self.put_db_last_key(new_last_key)
        
        return count