# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/12 23:04:00
# @modified 2022/03/19 18:54:15
import xutils
import math
import web.db
import typing

from xutils import dbutil
from xutils import Storage
from xutils import textutil, webutil
from xnote.core import xauth, xtables, xtemplate, xconfig
from xutils.sqldb import TableProxy, TempTableProxy
from xnote.plugin import DataTable, TabBox
from xnote.plugin import sidebar
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote_handlers.config import LinkConfig
from xutils.db.binlog import BinLog, BinLogOpType
from xnote.plugin import ListView, ListViewItem
from typing import List

def get_display_value(value: str):
    return textutil.get_short_text(value, 100)

def parse_bool(value):
    return value == "true"


class DbScanHandler:

    title = "数据库工具"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = "system"

    placeholder = "主键"
    btn_text = "查询"
    editable = False
    show_search = False
    show_title = False
    rows = 0

    @xauth.login_required("admin")
    def do_delete(self):
        key = xutils.get_argument_str("key", "")
        dbutil.db_delete(key)
        BinLog.add_log(optype=BinLogOpType.delete, key=key)
        return webutil.SuccessResult()

    @xauth.login_required("admin")
    def do_search(self):
        prefix = xutils.get_argument_str("prefix", "")
        cursor = xutils.get_argument_str("cursor", "")
        keyword = xutils.get_argument_str("keyword", "")
        reverse = xutils.get_argument_bool("reverse", False)
        q_user_name = xutils.get_argument_str("q_user_name", "")
        result = []

        if q_user_name != "":
            prefix = prefix + ":" + q_user_name
        
        if prefix != "" and prefix[-1] != ":":
            prefix += ":"

        limit = 200
        if reverse:
            key_from = None
            key_to = cursor
        else:
            key_from = cursor
            key_to = None

        if key_from == "":
            key_from = None
        if key_to == "":
            key_to = None

        scanned = 0
        next_cursor = ""
        keywords = textutil.split_words(keyword)

        for key, value in dbutil.prefix_iter(
                prefix, key_from=key_from, key_to=key_to, include_key=True, limit=limit+1,
                parse_json=False, reverse=reverse, scan_db=True):
            if scanned < limit and (textutil.contains_all(key, keywords) or textutil.contains_all(value, keywords)):
                item = Storage(key=key, key_encoded=xutils.quote(key), value=value, data_key=xutils.html_escape(key))
                result.append(item)
            scanned += 1
            next_cursor = key

        has_next = False
        if scanned > limit:
            scanned = limit
            has_next = True

        web_result = webutil.SuccessResult(data=result)
        web_result.has_next = has_next
        web_result.next_cursor = next_cursor
        web_result.scanned = scanned
        return web_result
    
    def do_list_meta(self):
        p2 = xutils.get_argument_str("p2")
        kw = Storage()
        kw.parent_link = LinkConfig.app_index
        kw.table_dict = dbutil.get_table_dict_copy()
        kw.get_display_value = get_display_value
        kw.table_names = dbutil.get_table_names()
        if p2 == "delete":
            kw.admin_stat_list = self.list_delete_table()
        elif p2 == "index":
            kw.admin_stat_list = self.list_table_by_type("index")
        elif p2 == "sorted_set":
            kw.admin_stat_list = self.list_table_by_type("sorted_set")
        elif p2 == "set":
            kw.admin_stat_list = self.list_table_by_type("set")
        else:
            self.handle_admin_stat_list(kw)
        return self.render_html(kw)

    def POST(self):
        return self.GET()

    @xauth.login_required("admin")
    def GET(self):
        action = xutils.get_argument_str("action", "")
        db_key = xutils.get_argument_str("db_key", "")
        q_user_name = xutils.get_argument_str("q_user_name", "")
        prefix = xutils.get_argument_str("prefix", "")
        reverse = xutils.get_argument_str("reverse", "")
        key_from = xutils.get_argument_str("key_from", "")
        p = xutils.get_argument_str("p")

        if action == "delete":
            return self.do_delete()

        if action == "search":
            return self.do_search()
        
        if p == "meta":
            return self.do_list_meta()

        result = []
        need_reverse = parse_bool(reverse)
        max_scan = 10000
        self.scan_count = 0
        self.error = ""
        self.last_key = ""

        real_prefix = prefix
        if q_user_name != "":
            real_prefix = prefix + ":" + q_user_name

        def func(key: str, value: str):
            # print("db_scan:", key, value)
            self.scan_count += 1
            if self.scan_count > max_scan:
                self.error = "too many scan"
                return False

            if not key.startswith(real_prefix):
                return False

            if db_key in value:
                self.last_key = key
                result.append((key, value))
                if len(result) > 30:
                    return False

            return True

        if key_from == "" and real_prefix != "":
            key_from = real_prefix + ":"

        key_to = b'\xff'
        if need_reverse:
            key_to = key_from.encode("utf8") + b'\xff'

        dbutil.db_scan(key_from=key_from, key_to=key_to, func=func,
                    reverse=need_reverse, parse_json=False)

        kw = Storage()
        kw.result = result
        kw.table_dict = dbutil.get_table_dict_copy()
        kw.prefix = prefix
        kw.db_key = db_key
        kw.reverse = reverse
        kw.get_display_value = get_display_value
        kw.error = self.error
        kw.last_key = self.last_key
        kw.table_names = dbutil.get_table_names()
        kw.q_user_name = q_user_name
        kw.is_reverse = (reverse == "true")
        kw.parent_link = LinkConfig.app_index

        self.handle_admin_stat_list(kw)
        return self.render_html(kw)

    def render_html(self, kw):
        p = xutils.get_argument_str("p", "")
        if p == "meta":
            return xtemplate.render("system/page/db/db_meta.html", **kw)
        return xtemplate.render("system/page/db/db_admin.html", **kw)

    def is_visible(self, table_info: dbutil.TableInfo, show_delete):
        if show_delete:
            return table_info.is_deleted
        else:
            return not table_info.is_deleted

    def handle_admin_stat_list(self, kw: Storage):
        p = xutils.get_argument_str("p", "")
        show_delete = xutils.get_argument_bool("show_delete", False)

        if p != "meta":
            return
        hide_index = xutils.get_argument_bool("hide_index", True)

        admin_stat_list = []
        if xauth.is_admin():
            table_dict = dbutil.get_table_dict_copy()
            table_values = sorted(table_dict.values(),
                                  key=lambda x: (x.category, x.name))
            for table_info in table_values:
                name = table_info.name
                if hide_index and name.find("$")>=0:
                    continue
                if not self.is_visible(table_info, show_delete):
                    continue
                table_count = dbutil.count_table(name, use_cache=True)
                admin_stat_list.append([table_info, table_count])

        kw.admin_stat_list = admin_stat_list
        kw.show_delete = show_delete

    def list_delete_table(self):
        result = []
        if xauth.is_admin():
            table_dict = dbutil.get_table_dict_copy()
            table_values = sorted(table_dict.values(),
                                  key=lambda x: (x.category, x.name))
            for table_info in table_values:
                name = table_info.name
                if table_info.is_deleted:
                    table_count = dbutil.count_table(name, use_cache=True)
                    result.append([table_info, table_count])

        return result

    def list_table_by_type(self, type="", include_deleted=False):
        result = []
        if xauth.is_admin():
            table_dict = dbutil.get_table_dict_copy()
            table_values = sorted(table_dict.values(),
                                  key=lambda x: (x.category, x.name))
            for table_info in table_values:
                name = table_info.name
                if not include_deleted and table_info.is_deleted:
                    continue
                if table_info.type == type:
                    table_count = dbutil.count_table(name, use_cache=True)
                    result.append([table_info, table_count])

        return result

class SqlDBInfo(Storage):
    def __init__(self):
        self.name = ""
        self.name_url = ""
        self.amount = 0
        self.comment = ""
        self.operate_url = ""
        self.struct_url = ""

class SqlDBAdminHandler:

    @staticmethod
    def sort_key(table_info: xtables.TableProxy):
        if table_info.table_name.startswith("plugin_"):
            return (1, table_info.table_name)
        return (0, table_info.table_name)

    def filter_tables(self, filter = ""):
        if filter == "delete":
            return xtables.get_all_tables(is_deleted=True)

        tables = xtables.get_all_tables(is_deleted=False)
        if filter == "plugin":
            return [p for p in tables if p.table_info.is_plugin]
        
        return [p for p in tables if not p.table_info.is_plugin]


    @xauth.admin_required()
    def GET(self):
        p2 = xutils.get_argument_str("p2")
        db_list = self.filter_tables(p2)
        db_list.sort(key = SqlDBAdminHandler.sort_key)
        db_info_table = DataTable()
        db_info_table.default_head_style.min_width = "120px"
        db_info_table.add_head("表名", field="name", link_field="name_url", min_width="150px")
        db_info_table.add_head("说明", field="comment", min_width="150px")
        db_info_table.add_head("记录数", field="amount")
        db_info_table.add_action(title="操作", type="link", link_field="operate_url", css_class="btn btn-default")
        db_info_table.add_action(title="结构", type="link", link_field="struct_url", css_class="btn btn-default")

        server_home = xconfig.WebConfig.server_home

        for db in db_list:
            info = SqlDBInfo()
            info.name = db.tablename
            info.name_url = f"{server_home}/system/sqldb_detail?name={info.name}"
            info.amount = db.count()
            info.comment = db.table_info.comment
            info.operate_url = f"{server_home}/system/sqldb_operate?table_name={info.name}"
            info.struct_url = f"{server_home}/system/db/struct?table_name={info.name}"

            db_info_table.add_row(info)

        filter_tab = TabBox(tab_key="p2", tab_default="active")
        filter_tab.add_tab(title="活跃", value="active")
        filter_tab.add_tab(title="插件", value="plugin")
        filter_tab.add_tab(title="删除", value="delete")

        kw = Storage()
        kw.db_info_table = db_info_table
        kw.parent_link = LinkConfig.app_index
        kw.filter_tab = filter_tab
        kw.db_nav_tab = "sqldb"
        return xtemplate.render("system/page/db/sqldb_list.html", **kw)

class SqlResult:
    def __init__(self, rows=[], count=0) -> None:
        self.rows = rows
        self.count = count
        self.pk_name = "id"

class SqlDBDetailHandler:

    def get_table_by_name(self, name):
        # type: (str) -> TableProxy
        return xtables.get_table_by_name(name)
    
    def get_kv_detail(self):
        key = xutils.get_argument_str("key")
        value = dbutil.db_get(key)
        return webutil.SuccessResult(data=xutils.tojson(value, format=True))
    
    def get_ext_db_rows(self, name="", page=1, page_size=20, dbpath=""):
        assert page_size <= 100
        result = SqlResult()
        db = xtables.MySqliteDB(db=dbpath)

        offset = webutil.get_page_offset(page=page, page_size=page_size)
        result.rows = list(db.select(name, offset=offset, limit=page_size)) # type: ignore
        result.count = db.select(name, what="count(1) AS amount").first().amount # type: ignore
        return result
    
    def get_db_rows(self, name="", page=1, page_size=20, dbpath=""):
        if dbpath != "":
            return self.get_ext_db_rows(name, page, page_size, dbpath)
        
        assert page_size <= 100
        db = self.get_table_by_name(name)
        table_info = db.table_info
        db_rows = []
        
        if db != None and table_info != None:
            pk_name = table_info.pk_name
            offset = (page-1) * page_size
            db_rows = db.select(offset = offset, limit = page_size, order = f"`{pk_name}` desc")
        
        result = SqlResult(rows = db_rows, count = db.count())
        result.pk_name = table_info.pk_name
        return result

    @xauth.admin_required()
    def GET(self):
        try:
            return self.do_get()
        except:
            error_stack = xutils.print_exc()
            return xtemplate.render("error.html", error = error_stack)

    def do_get(self):
        name = xutils.get_argument_str("name")
        page = xutils.get_argument_int("page", 1)
        page_size = xutils.get_argument_int("page_size", 20)
        method = xutils.get_argument_str("method")
        dbpath = xutils.get_argument_str("dbpath")
        if method == "get_kv_detail":
            return self.get_kv_detail()
        
        result = self.get_db_rows(name=name, page=page, page_size=page_size, dbpath=dbpath)
        page_max = math.ceil(result.count / page_size) // 1
    

        kw = Storage()
        kw.parent_link = LinkConfig.app_index
        kw.db_rows = result.rows
        kw.pk_name = result.pk_name
        kw.page = page
        kw.page_size = page_size
        kw.page_max = page_max
        kw.page_url = f"?name={name}&dbpath={xutils.quote(dbpath)}&page_size={page_size}&page="
        kw.table_name = name
        kv_table_info = dbutil.TableInfo.get_kv_table_by_index(name)
        if kv_table_info != None:
            kw.kv_table_name = kv_table_info.name
        else:
            kw.kv_table_name = None
        return xtemplate.render("system/page/db/sqldb_detail.html", **kw)

class SqlDBOperateHandler:

    @xauth.login_required("admin")
    def GET(self):
        table_name = xutils.get_argument_str("table_name")
        dbpath = xutils.get_argument_str("dbpath")
        if dbpath != "":
            dbpath = xutils.quote(dbpath)
            raise web.found(f"/system/sqlite?table_name={table_name}&path={dbpath}")
        
        db = xtables.get_table_by_name(table_name)
        if isinstance(db.db, xtables.MySqliteDB):
            dbpath = xutils.quote(db.db.dbpath)
            raise web.found(f"/system/sqlite?table_name={table_name}&path={dbpath}")
        if isinstance(db.db, web.db.MySQLDB):
            raise web.found(f"/system/sqlite?type=mysql&table_name={table_name}")
        return "not ready"

class DropTableHandler:

    @xauth.login_required("admin")
    def POST(self):
        table_name = xutils.get_argument_str("table_name")
        db = dbutil.get_table(table_name)
        if not db.table_info.is_deleted:
            return dict(code="400", message="只能清空删除的表")
        
        for item in db.iter(limit=-1):
            db.delete(item)
        
        dbutil.count_table(table_name, use_cache=False)
        return dict(code="success")


class DatabaseInfoRow(Storage):
    def __init__(self, name="", value="", remark=""):
        self.name = name
        self.value = value
        self.remark = remark

class DatabaseDriverInfoHandler(BaseTablePlugin):

    require_admin = True
    title = "数据库引擎信息"
    NAV_HTML = ""
    show_aside = True
    parent_link = LinkConfig.system_info

    def get_aside_html(self):
        return sidebar.get_admin_sidebar_html()

    def handle_page(self):
        type = xutils.get_argument_str("type")
        kw = Storage()
        if type == "sql":
            info_list = self.get_sql_driver_info_list()
        else:
            info_list = self.get_kv_driver_info_list()

        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head("名称", field="name")
        table.add_head("描述", field="value")
        table.add_head("备注", field="remark")

        for row in info_list:
            table.add_row(row)

        kw.table = table
        return self.response_page(**kw)
    
    def format_pragma(self, pragma="", result=""):
        if pragma == "synchronous":
            if result == "0":
                result += " (off)"
            if result == "1":
                result += " (normal)"
            if result == "2":
                result += " (full)"
        return result

    def get_sqlite_pragma(self, db: web.db.SqliteDB, pragma: str):
        db_result = db.query("pragma %s" % pragma)
        if isinstance(db_result, web.db.BaseResultSet):
            first = db_result.first()
            if isinstance(first, dict):
                result = self.format_pragma(pragma, str(first.get(pragma)))
            else:
                result = "None"
        else:
            result = str(db_result)
        return DatabaseInfoRow(pragma, result)
    
    def get_mysql_variable(self, db: web.db.DB, var_name, format_size=False):
        # TODO 可以一次性取出所有的变量
        if not hasattr(self, "mysql_vars"):
            self.mysql_vars = {}
            for item in db.query("show variables"): # type: ignore
                key = item.get("Variable_name")
                value = item.get("Value")
                self.mysql_vars[key] = value
                
        result = self.mysql_vars.get(var_name, "")
        if textutil.is_number(result):
            value_int = int(result)
            result += f" ({xutils.format_size(value_int)})"
        return DatabaseInfoRow(var_name, result)
    
    def get_sql_driver_info_list(self):
        info_list = [DatabaseInfoRow("db_driver", xconfig.DatabaseConfig.db_driver_sql)]
        if xconfig.DatabaseConfig.db_driver_sql == "sqlite":
            info_list += self.get_sqlite_info(xtables.get_default_db_instance())
        elif xconfig.DatabaseConfig.db_driver_sql == "mysql":
            info_list += self.get_mysql_info()
        return info_list
    
    def get_mysql_info(self):
        db = xtables.get_default_db_instance()
        info_list: typing.List[DatabaseInfoRow] = []
        var_name_list = [
            "key_buffer_size",
            "table_open_cache",
            "sort_buffer_size",
            "read_buffer_size",
            "open_files_limit",
            "innodb_buffer_pool_size",
            "innodb_flush_log_at_trx_commit",
            "sync_binlog",
            "max_allowed_packet",
        ]
        for var_name in var_name_list:
            info_list.append(self.get_mysql_variable(db, var_name))
        return info_list
    
    def get_sqlite_info(self, db):
        assert isinstance(db, xtables.MySqliteDB)
        info_list = [DatabaseInfoRow("db_path", db.dbpath)]
        pragma_list = [
            "journal_mode", "journal_size_limit","synchronous",
            "cache_size", "data_version", "busy_timeout", "encoding",
            "mmap_size", "locking_mode", "wal_autocheckpoint",
            "page_count", "page_size", "max_page_count"
        ]
        for pragma in pragma_list:
            info_list.append(self.get_sqlite_pragma(db, pragma))
        return info_list

    def get_kv_driver_info_list(self):
        info_list = [DatabaseInfoRow("db_driver", xconfig.DatabaseConfig.db_driver)]
        instance = dbutil.get_instance()
        if xconfig.DatabaseConfig.db_driver == "sqlite":
            db = xtables.get_db_instance(xconfig.FileConfig.kv_db_file)
            info_list += self.get_sqlite_info(db)
        if xconfig.DatabaseConfig.db_driver == "leveldb":
            from xutils.db.driver_leveldb import LevelDBImpl
            assert isinstance(instance, LevelDBImpl)
            info_list += [DatabaseInfoRow("Stats", instance.GetStats())]

        return info_list

class TableData:
    def __init__(self, head=[], items=[]):
        self.head = head
        self.items: List[dict] = items # items

    def to_data_table(self):
        result = DataTable()

        min_width_dict = {
            "name": "150px",
            "dflt_value": "150px",
            "type": "150px",
        }

        for head in self.head:
            min_width = min_width_dict.get(head, "100px")
            result.add_head(title=head, field=head, min_width=min_width)
        result.set_rows(self.items)
        return result
    
    def to_list_view(self):
        result = ListView()
        for item in self.items:
            list_item = ListViewItem()
            for head in self.head:
                value = item.get(head, "")
                if value == "":
                    continue
                list_item.add_span(f"{head}: ", css_class="bold")
                list_item.add_span(value)
                list_item.add_br()
            result.add_item(list_item)
        return result


class StructHelper:
    
    def __init__(self, table_proxy: xtables.TableProxy):
        self.table_proxy = table_proxy
    
    def result_set_to_table(self, result_set: web.db.BaseResultSet, table_proxy: typing.Optional[xtables.TableProxy] = None):
        result = TableData()
        comment_name = []
        items = list(result_set.list())

        if table_proxy != None and table_proxy.db_type == "sqlite":
            table_info = table_proxy.get_table_info()
            for item_info in items:
                # 仅在sqlite环境下生效
                colname = item_info.get("name", "")
                old_comment = item_info.get("comment")
                if old_comment != None:
                    continue
                comment = table_info.get_column_comment(colname)
                item_info.comment = comment
            comment_name = ["comment"]

        result.head = result_set.names + comment_name
        result.items = items
        return result
    
    def get_index_info(self):
        table_proxy = self.table_proxy
        table_info = table_proxy.table_info
        db_type = table_info.db_type

        if db_type == "sqlite":
            vars = dict(type="index", tbl_name=table_info.table_name)
            result_set = table_proxy.raw_query("select name, sql from sqlite_master where type=$type AND tbl_name=$tbl_name", vars=vars)
            assert isinstance(result_set, web.db.BaseResultSet)
            return self.result_set_to_table(result_set, table_proxy)

        if db_type == "mysql":
            vars = dict(database=xconfig.DatabaseConfig.mysql_database, table_name=table_info.table_name)
            # 完整字段查看 DESC information_schema.statistics
            result_set = table_proxy.raw_query("SELECT index_name,seq_in_index,column_name,non_unique,nullable,index_type,comment,index_comment \
                                               FROM information_schema.statistics WHERE table_schema=$database AND table_name = $table_name", vars=vars)
            assert isinstance(result_set, web.db.BaseResultSet)
            return self.result_set_to_table(result_set, table_proxy)
        
        return TableData()

    def get_column_info(self):
        table_proxy = self.table_proxy
        table_name = table_proxy.table_name
        table_info = table_proxy.table_info
        db_type = table_info.db_type

        if db_type == "sqlite":
            result_set = table_proxy.raw_query(f"pragma table_info({table_name})")
            assert isinstance(result_set, web.db.BaseResultSet)
            return self.result_set_to_table(result_set, table_proxy)
    
        if db_type == "mysql":
            result_set = table_proxy.raw_query(f"DESC `{table_name}`")
            assert isinstance(result_set, web.db.BaseResultSet)
            return self.result_set_to_table(result_set, table_proxy)
        return TableData()
    
    def get_create_sql(self):
        if self.table_proxy.db_type == "sqlite":
            vars = dict(type="table", tbl_name=self.table_proxy.table_name)
            rows = self.table_proxy.query("select name, sql from sqlite_master where type=$type AND tbl_name=$tbl_name", vars=vars)
            assert len(rows) > 0
            return rows[0]["sql"]
        return ""

class SqliteStructHelper(StructHelper):

    def __init__(self, table_name="", dbpath=""):
        self.db = web.db.SqliteDB(db=dbpath)
        self.table_name = table_name

    def get_index_info(self):
        vars = dict(type="index", tbl_name=self.table_name)
        result_set = self.db.query("select name, sql from sqlite_master where type=$type AND tbl_name=$tbl_name order by name", vars=vars)
        assert isinstance(result_set, web.db.BaseResultSet)
        return self.result_set_to_table(result_set, None)

    def get_column_info(self):
        result_set = self.db.query(f"pragma table_info({self.table_name})")
        assert isinstance(result_set, web.db.BaseResultSet)
        return self.result_set_to_table(result_set, None)
    
    def get_create_sql(self):
        vars = dict(type="table", tbl_name=self.table_name)
        row = self.db.query("select name, sql from sqlite_master where type=$type AND tbl_name=$tbl_name", vars=vars).first() # type: ignore
        assert row != None
        return row["sql"]

class StructHandler:

    @xauth.admin_required()
    def GET(self):
        dbpath = xutils.get_argument_str("dbpath")
        table_name = xutils.get_argument_str("table_name")

        if dbpath == "":
            table_proxy = xtables.get_table_by_name(table_name)
            helper = StructHelper(table_proxy)
        else:
            helper = SqliteStructHelper(table_name=table_name, dbpath=dbpath)

        column_info = helper.get_column_info()
        index_info = helper.get_index_info()

        kw = Storage()
        kw.table_name = table_name
        kw.create_sql = helper.get_create_sql()
        kw.error = ""
        kw.column_table = column_info.to_data_table()
        kw.index_info = index_info.to_list_view()
        kw.title = f"表结构 - {table_name}"
        kw.parent_link = LinkConfig.sqldb_admin

        return xtemplate.render("system/page/db/db_struct.html", **kw)

xurls = (
    "/system/db_scan", DbScanHandler,
    "/system/db_admin", DbScanHandler,
    "/system/leveldb_admin", DbScanHandler,
    "/system/sqldb_admin", SqlDBAdminHandler,
    "/system/sqldb_detail", SqlDBDetailHandler,
    "/system/sqldb_operate", SqlDBOperateHandler,
    "/system/db/drop_table", DropTableHandler,
    "/system/db/driver_info", DatabaseDriverInfoHandler,
    "/system/db/struct", StructHandler,
)
