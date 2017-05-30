# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/12
# 

"""Description here"""

import os
import time
import web
import xutils
import xconfig

from . import dao

class handler:

    def GET(self):
        id = xutils.get_argument("id", type = int)
        file = dao.get_by_id(id)
        random_file_name = str(time.time()) + ".md"
        random_file_path = os.path.join(xconfig.TMP_DIR, random_file_name)
        with open(random_file_path, "w", encoding="utf-8") as fp:
            fp.write(file.content)
        raise web.seeother("/tmp/" + random_file_name)
