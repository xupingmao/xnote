# encoding=utf-8
# Created by xupingmao on 2017/06/23
# Last Modified on 2018/01/18
import time
import web
import xauth
import xtables
import xutils
import xconfig
from xutils import dbutil

dbutil.register_table("record", "系统日志表")
_db = dbutil.get_table("record")

def save_ip(real_ip):
    if real_ip is not None:
        # 处理X-Forwarded-For
        real_ip = real_ip.split(",")[0]
        # 跳过内网
        # A类和C类
        if real_ip.startswith("10.") or real_ip.startswith("192.168") or real_ip == "127.0.0.1":
            return
        db = xtables.get_record_table()
        record = db.select_first(where=dict(type="ip", key=real_ip, cdate=xutils.format_date()))
        if record is None:
            db.insert(type="ip", key=real_ip, cdate=xutils.format_date(), 
                ctime=xutils.format_datetime(), value="1")
        else:
            db.update(value=int(record.value)+1, where=dict(id=record.id))

SCRIPT = """
if (navigator.geolocation && window.xuser != "") {
    navigator.geolocation.getCurrentPosition(function (pos) {
        console.log(pos);
        if (pos && pos.coords) {
            // JSON.stringify 无效
            var latitude = pos.coords.latitude;
            var longitude = pos.coords.longitude;
            var accuracy = pos.coords.accuracy;

            var coords = {
                latitude: latitude, 
                longitude:longitude, 
                accuracy: accuracy,
                heading: pos.coords.heading,
                speed: pos.coords.speed,
                altitude: pos.coords.altitude,
                altitudeAccuracy: pos.coords.altitudeAccuracy
            };
            $.post("/system/stats/location", {coords: JSON.stringify(coords)});
        }
    });
}

"""

class handler:

    def GET(self):
        # X-Forwarded-For是RFC 7239（Forwarded HTTP Extension）定义的扩展首部，大部分代理支持
        # 格式如下：
        # X-Forwarded-For: client, proxy1, proxy2
        # 而X-Real-IP目前不属于任何标准
        # See https://imququ.com/post/x-forwarded-for-header-in-http.html
        # save_ip(web.ctx.env.get("HTTP_X_FORWARDED_FOR"))
        # save_ip(web.ctx.env.get("REMOTE_ADDR"))
        
        # web.header("Cache-Control", "max-age=600")
        environ = web.ctx.environ
        content = "/* empty */"

        web.header("Content-Type", "application/javascript")
        client_etag = environ.get('HTTP_IF_NONE_MATCH')

        if client_etag == None or client_etag == "":
            client_etag_val = 0
        else:
            client_etag_val = float(client_etag)

        if time.time() - client_etag_val > 600:
            # 采集数据时间区间
            save_ip(web.ctx.env.get("HTTP_X_FORWARDED_FOR"))
            save_ip(web.ctx.env.get("REMOTE_ADDR"))
            if xconfig.WebConfig.record_location:
                content = SCRIPT

        if not xauth.is_admin():
            content = "/* empty */"
        web.header("Etag", time.time())
        return content

class LocationHandler:

    def POST(self):
        coords = xutils.get_argument("coords")
        if coords != "null":
            data = dict(type="location", key=xauth.get_current_name(), cdate=xutils.format_date(), 
                ctime=xutils.format_datetime(), value=coords)
            _db.insert(data)
        return "{}"


xurls = (
    r"/system/stats", handler,
    r"/system/stats/location", LocationHandler
)