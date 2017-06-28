# encoding=utf-8
# Created by xupingmao on 2017/06/23
import web
import xtables
import xutils

def save_ip(real_ip):
    if real_ip is not None:
        # 跳过内网
        # A类和C类
        if real_ip.startswith("10.") or real_ip.startswith("192.168"):
            return
        db = xtables.get_record_table()
        record = db.select_one(where=dict(type="ip", key=real_ip, cdate=xutils.format_date()))
        if record is None:
            db.insert(type="ip", key=real_ip, cdate=xutils.format_date(), 
                ctime=xutils.format_datetime(), value="1")
        else:
            db.update(value=int(record.value)+1, where=dict(id=record.id))

class handler:

    def GET(self):
        save_ip(web.ctx.env.get("HTTP_X_REAL_IP"))
        save_ip(web.ctx.env.get("REMOTE_ADDR"))
        
        web.header("Content-Type", "application/javascript")
        return "/** stats **/"