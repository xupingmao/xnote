# encoding=utf-8
# Created by xupingmao on 2017/06/23
# Last Modified on 2017/06/28
import web
import xtables
import xutils

def save_ip(real_ip):
    if real_ip is not None:
        # 处理X-Forwarded-For
        real_ip = real_ip.split(",")[0]
        # 跳过内网
        # A类和C类
        if real_ip.startswith("10.") or real_ip.startswith("192.168") or real_ip == "127.0.0.1":
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
        # X-Forwarded-For是RFC 7239（Forwarded HTTP Extension）定义的扩展首部，大部分代理支持
        # 格式如下：
        # X-Forwarded-For: client, proxy1, proxy2
        # 而X-Real-IP目前不属于任何标准
        # See https://imququ.com/post/x-forwarded-for-header-in-http.html
        save_ip(web.ctx.env.get("HTTP_X_FORWARDED_FOR"))
        save_ip(web.ctx.env.get("REMOTE_ADDR"))
        
        web.header("Cache-Control", "max-age=3600")
        web.header("Content-Type", "application/javascript")
        return "/** stats **/"