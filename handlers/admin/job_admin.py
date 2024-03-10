# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 16:15:53
@LastEditors  : xupingmao
@LastEditTime : 2024-03-10 18:09:24
@FilePath     : /xnote/handlers/admin/job_admin.py
@Description  : 描述
"""

from xnote.core.xtemplate import BasePlugin
from xutils import Storage
from xutils import webutil
from xnote.core.template import DataTable
from xnote.service import JobService, SysJob
from xnote.core import xauth
import xutils

HTML = r"""
<div class="card">
    {% include common/table/table.html %}
</div>

<div class="card">
    {% include common/pagination.html %}
</div>

"""

ASIDE_HTML = """
{% include system/component/admin_nav.html %}
"""

class JobHandler(BasePlugin):
    
    title = '任务管理'
    show_edit = False
    rows = 0
    
    def handle(self, content):
        functions = []
        page = xutils.get_argument_int("page", 1)
        page_size = 20
        
        assert page >= 1
        
        table = DataTable()
        table.add_head("ID", "id", width="10%")
        table.add_head("更新时间", "mtime", width="20%")
        table.add_head("任务类型", "job_type", width="10%")
        table.add_head("任务状态", "job_status", width="10%")
        table.add_head("任务结果", "job_result")
        
        job_list, total = JobService.list_job_page(offset=(page-1)*page_size, limit=page_size)
        
        for job_info in job_list:
            table.add_row(job_info.__dict__)
        
        pagination = webutil.Pagination(page=1, total=total)
        kw = Storage()
        kw.functions = functions
        kw.table = table
        kw.page = page
        kw.page_max = pagination.page_max
        kw.page_url = "?page="
        
        self.writehtml(HTML, **kw)
        self.write_aside(ASIDE_HTML)
    
class JobTestHandler:
    
    @xauth.login_required("admin")
    def GET(self):
        job_info = SysJob()
        job_info.job_type = "test"
        with JobService.run_with_job(job_info):
            job_info.job_result = "success"
        return webutil.SuccessResult()
    
xurls = (
    r"/admin/jobs", JobHandler,
    r"/admin/test_job", JobTestHandler
)