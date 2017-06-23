# encoding=utf-8
# Created by xupingmao on 2017/06/23
import web
import xtables
import xutils

class handler:

    def GET(self):
        real_ip = web.ctx.env.get("HTTP_X_REAL_IP")
        if real_ip is not None:
            db = xtables.get_record_table()
            record = db.select_one(where=dict(type="ip", key=real_ip, cdate=xutils.format_date()))
            if record is None:
                db.insert(type="ip", key=real_ip, cdate=xutils.format_date(), 
                    ctime=xutils.format_datetime(), value="1")
        web.header("Content-Type", "application/javascript")
        return "/** stats **/"