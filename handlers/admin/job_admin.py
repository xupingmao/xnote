# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 22:56:56
@LastEditors  : xupingmao
@LastEditTime : 2024-04-20 16:50:19
@FilePath     : /xnote/handlers/admin/job_admin.py
@Description  : 描述
"""
import time
from xnote.core.xtemplate import BasePlugin
from xutils import Storage
from xutils import webutil
from xnote.plugin import DataTable, DataForm
from xnote.service import JobService, SysJob, JobStatusEnum
from xnote.core import xauth
from xutils import dateutil
import xutils
import json

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

VIEW_HTML = """
<div class="card">
    <textarea class="row" rows=20>{{job_info}}</textarea>
</div>
"""

VIEW_FORM_HTML = """
{% include common/form/form.html %}
"""

class JobHandler(BasePlugin):
    
    title = '任务管理'
    show_edit = False
    rows = 0
    
    def handle_view(self):
        self.show_nav = False
        self.show_title = False
        
        job_id = xutils.get_argument_int("job_id")
        job_info = JobService.get_job_by_id(job_id=job_id)
        kw = Storage()
        kw.job_info = xutils.tojson(xutils.obj2dict(job_info), format=True)
        self.writehtml(VIEW_HTML, **kw)
        self.write_aside(ASIDE_HTML) 

    def handle_edit(self):
        self.show_nav = False
        self.show_title = False
        
        job_id = xutils.get_argument_int("job_id")
        job_info = JobService.get_job_by_id(job_id=job_id)
        kw = Storage()
        kw.job_info = xutils.tojson(xutils.obj2dict(job_info), format=True)

        if job_info != None:
            form = DataForm()
            form.add_row("ID", "id", value=str(job_info.id), readonly=True)
            form.add_row("创建时间", "ctime", value=job_info.ctime, readonly=True)
            form.add_row("更新时间", "mtime", value=job_info.mtime, readonly=True)
            
            row = form.add_row("任务类型", "job_type", value=str(job_info.job_type), type="select")
            row.add_option("数据库备份", "db_backup")
            row.add_option("测试", "test")
            
            form.add_row("任务参数", "job_params", value=job_info.job_params, type="textarea")
            form.add_row("任务结果", "job_result", value=job_info.job_result, type="textarea")
            kw.form = form
        
        return self.response_ajax(VIEW_FORM_HTML, **kw)
        
    def handle_delete(self):
        job_id = xutils.get_argument_int("job_id")
        JobService.delete_by_id(job_id=job_id)
        return webutil.SuccessResult()
    
    def handle_save(self):
        data_json = xutils.get_argument_str("data")
        data_dict = json.loads(data_json)
        
        job_id = data_dict.get("id")
        job_info = JobService.get_job_by_id(job_id=job_id)
        if job_info == None:
            return webutil.FailedResult(code="404", message="数据不存在")


        job_info.job_type = data_dict.get("job_type")
        JobService.update_job(job_info)
        return webutil.SuccessResult()

    def handle(self, content):
        action = xutils.get_argument_str("action")
        
        if action == "view":
            return self.handle_view()
        if action == "edit":
            return self.handle_edit()
        if action == "save":
            return self.handle_save()
        if action == "delete":
            return self.handle_delete()
        
        page = xutils.get_argument_int("page", 1)
        page_size = 20
        
        assert page >= 1
        
        table = DataTable()
        table.add_head("ID", "id", width="10%")
        table.add_head("更新时间", "mtime", width="20%")
        table.add_head("任务类型", "job_type", width="20%")
        table.add_head("任务状态", "status_title", width="20%")
        
        table.add_action("查看详情", link_field="view_url")
        table.add_action("编辑", link_field="edit_url", type="edit_form")
        table.add_action("删除", type="confirm", link_field="delete_url", msg_field="delete_msg", css_class="btn danger")
        
        job_list, total = JobService.list_job_page(offset=(page-1)*page_size, limit=page_size)
        
        for job_info in job_list:
            row = job_info.__dict__
            row["status_title"] = JobStatusEnum.get_title_by_status(job_info.job_status)
            row["view_url"] = f"?action=view&job_id={job_info.id}"
            row["edit_url"] = f"?action=edit&job_id={job_info.id}"
            row["delete_url"] = f"?action=delete&job_id={job_info.id}"
            row["delete_msg"] = f"确认删除记录【{job_info.id}】吗?"
            table.add_row(row)
        
        pagination = webutil.Pagination(page=1, total=total)
        kw = Storage()
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
            time.sleep(1)
            job_info.job_result = "success"
            job_info.mtime = dateutil.format_datetime()
        return webutil.SuccessResult()
    
xurls = (
    r"/admin/jobs", JobHandler,
    r"/admin/test_job", JobTestHandler
)