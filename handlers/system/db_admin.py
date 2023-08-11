# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/02/12 23:04:00
# @modified 2022/03/19 18:54:15
import xutils
import xauth
from xutils import dbutil
from xutils import Storage
from xutils import textutil
import xtables
import xtemplate
import math
import xconfig
import web.db
from xutils.sqldb import TableProxy

def get_display_value(value):
    if value is None:
        return value

    if len(value) > 100:
        return value[:100] + "..."
    return value


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
        key = xutils.get_argument("key", "")
        dbutil.delete(key)
        return dict(code="success")

    @xauth.login_required("admin")
    def do_search(self):
        prefix = xutils.get_argument_str("prefix", "")
        cursor = xutils.get_argument("cursor", "")
        keyword = xutils.get_argument("keyword", "")
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
                item = Storage(key=key, value=value)
                result.append(item)
            scanned += 1
            next_cursor = key

        has_next = False
        if scanned > limit:
            scanned = limit
            has_next = True

        return dict(code="success", data=result, has_next=has_next, next_cursor=next_cursor, scanned=scanned)
    
    def do_list_meta(self):
        p2 = xutils.get_argument_str("p2")
        kw = Storage()
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
        action = xutils.get_argument("action", "")
        db_key = xutils.get_argument("db_key", "")
        q_user_name = xutils.get_argument_str("q_user_name", "")
        prefix = xutils.get_argument_str("prefix", "")
        reverse = xutils.get_argument("reverse", "")
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

        def func(key, value):
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

        dbutil.scan(key_from=key_from, key_to=key_to, func=func,
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

        self.handle_admin_stat_list(kw)
        return self.render_html(kw)

    def render_html(self, kw):
        p = xutils.get_argument("p", "")
        if p == "meta":
            return xtemplate.render("system/page/db/db_meta.html", **kw)
        return xtemplate.render("system/page/db/db_admin.html", **kw)

    def is_visible(self, table_info: dbutil.TableInfo, show_delete):
        if show_delete:
            return table_info.is_deleted
        else:
            return not table_info.is_deleted

    def handle_admin_stat_list(self, kw):
        p = xutils.get_argument("p", "")
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

    def list_table_by_type(self, type=""):
        result = []
        if xauth.is_admin():
            table_dict = dbutil.get_table_dict_copy()
            table_values = sorted(table_dict.values(),
                                  key=lambda x: (x.category, x.name))
            for table_info in table_values:
                name = table_info.name
                if table_info.type == type:
                    table_count = dbutil.count_table(name, use_cache=True)
                    result.append([table_info, table_count])

        return result

class SqlDBInfo:

    def __init__(self):
        self.name = ""
        self.amount = 0

class SqlDBHandler:

    @xauth.login_required("admin")
    def GET(self):
        db_list = xtables.get_all_tables()
        db_info_list = []
        for db in db_list:
            info = SqlDBInfo()
            info.name = db.tablename
            info.amount = db.count()
            db_info_list.append(info)
        kw = Storage()
        kw.db_info_list = db_info_list
        return xtemplate.render("system/page/db/sqldb_list.html", **kw)

class SqlDBDetailHandler:

    def get_table_by_name(self, name):
        # type: (str) -> TableProxy
        return xtables.get_table_by_name(name)

    @xauth.login_required("admin")
    def GET(self):
        name = xutils.get_argument_str("name")
        page = xutils.get_argument_int("page", 1)
        page_size = xutils.get_argument_int("page_size", 20)
        assert page_size <= 100
        db = self.get_table_by_name(name)
        db_rows = []
        page_max = 0
        if db != None:
            offset = (page-1) * page_size
            db_rows = db.select(offset = offset, limit = page_size, order = "id desc")
            page_max = math.ceil(db.count() / page_size) // 1

        kw = Storage()
        kw.db_rows = db_rows
        kw.page = page
        kw.page_size = page_size
        kw.page_max = page_max
        kw.page_url = "?name={name}&page_size={page_size}&page=".format(name = name, page_size=page_size)
        return xtemplate.render("system/page/db/sqldb_detail.html", **kw)

class SqlDBOperateHandler:

    @xauth.login_required()
    def GET(self):
        table_name = xutils.get_argument_str("table_name")
        db = xtables.get_table_by_name(table_name)
        if isinstance(db.db, xtables.MySqliteDB):
            raise web.seeother("/system/sqlite?path=" + xutils.quote(db.db.dbpath))
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

class DatabaseDriverInfoHandler:

    @xauth.login_required("admin")
    def GET(self):
        kw = Storage()
        kw.info_text = self.get_driver_info_text()
        return xtemplate.render("system/page/db/driver_info.html", **kw)

    def get_sqlite_pragma(self, db: web.db.SqliteDB, pragma):
        result = db.query("pragma %s" % pragma).first().get(pragma)
        return "\n\n%s: %s" % (pragma, result)

    def get_driver_info_text(self):
        info = "%s: %s" % ("db_driver", xconfig.DatabaseConfig.db_driver)
        instance = dbutil.get_instance()
        if xconfig.DatabaseConfig.db_driver == "sqlite":
            db = xtables.get_db_instance(xconfig.FileConfig.record_db_file)
            assert isinstance(db, web.db.SqliteDB)
            info += self.get_sqlite_pragma(db, "journal_mode")
            info += self.get_sqlite_pragma(db, "journal_size_limit")
            info += self.get_sqlite_pragma(db, "synchronous")
            info += self.get_sqlite_pragma(db, "cache_size")
            info += self.get_sqlite_pragma(db, "data_version")
            info += self.get_sqlite_pragma(db, "busy_timeout")
            info += self.get_sqlite_pragma(db, "encoding")
            info += self.get_sqlite_pragma(db, "mmap_size")
            info += self.get_sqlite_pragma(db, "locking_mode")
            info += self.get_sqlite_pragma(db, "wal_autocheckpoint")
            info += self.get_sqlite_pragma(db, "page_count")
            info += self.get_sqlite_pragma(db, "page_size")
            info += self.get_sqlite_pragma(db, "max_page_count")

        return info

xurls = (
    "/system/db_scan", DbScanHandler,
    "/system/db_admin", DbScanHandler,
    "/system/leveldb_admin", DbScanHandler,
    "/system/sqldb_admin", SqlDBHandler,
    "/system/sqldb_detail", SqlDBDetailHandler,
    "/system/sqldb_operate", SqlDBOperateHandler,
    "/system/db/drop_table", DropTableHandler,
    "/system/db/driver_info", DatabaseDriverInfoHandler,
)
