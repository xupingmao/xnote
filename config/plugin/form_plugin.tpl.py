# -*- coding:utf-8 -*-
# @id $plugin_id
# @api-level 2.8
# @since $since
# @author $author
# @version 1.0.0
# @category note
# @title 我的表单插件-$date
# @description 插件描述
# @icon-class fa-cube
# @permitted-role admin # 对admin用户开放
# @debug true # 开启调试模式，开发完成后记得关闭

import xconfig
import xutils
import xauth
import xmanager
import xtemplate
from xutils import Storage
from xutils import dbutil
from xutils import textutil
from xtemplate import BasePlugin

HTML = """
<!-- 操作区域 -->
<div class="card btn-line-height">
    <span>插件功能说明...</span>
    <div class="float-right">
        <button class="edit-btn">添加记录</button>
        <button class="option-btn btn-default">选项</button>
    </div>
</div>

<!-- 输出的表格 -->
<div class="card">
    <table class="table">
        <tr>
            <th>姓名</th>
            <th>年龄</th>
            <th>职业</th>
            <th>操作</th>
        </tr>
        
        {% for row in data_list %}
            <tr>
                <td>{{row.name}}</td>
                <td>{{row.age}}</td>
                <td>{{row.job}}</td>
                <td>
                    <button class="edit-btn btn-default" data-key="{{row._key}}">编辑</button>
                    <button class="delete-btn btn-danger" data-key="{{row._key}}">删除</button>
                </td>
            </tr>
        {% end %}
    </table>
</div>

<!-- 选项的HTML -->
<div class="option-html hide">
    <ul>
        <li>选项1</li>
        <li>选项2</li>
    </ul>
</div>

<!-- 编辑脚本 -->
<script>
$(function(){
    // 编辑事件处理(创建和更新)
    $(".edit-btn").click(function (event) {
        var rowKey  = $(event.target).attr("data-key");
        $.get("?action=get_template", {key: rowKey}, function(resp) {
            var buttons = ["确认", "取消"];
            var functions = [function (index, layero) {
                var params = $(".x-form").formData();
                params.key = rowKey;
                $.post("?action=edit", params, function (resp) {
                    if (resp.code != "success") {
                        xnote.alert(resp.message);
                    } else {
                        window.location.reload();
                    }
                }).fail(function (e) {
                    console.error(e);
                    xnote.alert("请求编辑接口失败");
                });
            }];
            xnote.showDialog("编辑行", resp, buttons, functions);
        });
    });

    // 删除事件处理
    $(".delete-btn").click(function (event) {
        var rowKey = $(event.target).attr("data-key");
        xnote.confirm("确认删除记录?", function (confirmed) {    
            $.post("?action=delete", {key: rowKey}, function (resp) {
                if (resp.code != "success") {
                    xnote.alert(resp.message);
                } else {
                    window.location.reload();
                }
            }).fail(function (e) {
                console.error(e);
                xnote.alert("请求删除接口失败");
            });
        });
    });

    // 选项事件处理
    $(".option-btn").click(function (event) {
        var option = {};
        option.html = $(".option-html").html();
        xnote.showOptionDialog(option);
    });
});
</script>
"""

EDIT_HTML = """
<form class="x-form" method="POST">
    <textarea class="col-md-12" name="content" rows=20>{{content}}</textarea>
</form>
"""

DEFAULT_EDIT_CONTENT = """
name = 张三
age  = 20
job  = 学生
"""


# 注册存储
dbutil.register_table("form_test_data", "表单测试数据")
TABLE = dbutil.LdbTable("form_test_data")


def convert_content_to_row(content):
    """把纯文本转换为键值对属性
    @param {str} content 输入的文本
    @return {Storage} 行对象
    """
    if content is None or content == "":
        return Storage(_content = content)

    row = Storage()
    properties = textutil.parse_prop_text(content)
    row.update(properties)
    row._content = content
    return row

def convert_row_to_content(row):
    """把键值对属性转换为文本"""
    if row is None:
        return DEFAULT_EDIT_CONTENT
    return row._content

def convert_data_list(data_list):
    """数据列表转换"""
    return data_list

class Main(BasePlugin):

    rows = 0

    def get_input_template(self):
        key = xutils.get_argument("key", "")
        row = TABLE.get_by_key(key)        
        
        # 转换成文本对象
        content = convert_row_to_content(row)
            
        return self.ajax_response(EDIT_HTML, content = content)
    
    def edit_row(self):
        key = xutils.get_argument("key", "")
        content = xutils.get_argument("content", "")
        user_name = xauth.current_name()

        # 转换对象
        row = convert_content_to_row(content)

        if key != "":
            TABLE.update_by_key(key, row)
            return dict(code = "success", message = "更新成功")
        else:
            TABLE.insert_by_user(user_name, row, id_type = "timeseq")
            return dict(code = "success", message = "创建成功")

    def delete_row(self):
        key = xutils.get_argument("key", "")
        user_name = xauth.current_name()
        if TABLE.is_valid_key(key, user_name = user_name):
            TABLE.delete_by_key(key)
            return dict(code = "success", message = "删除成功")
        else:
            return dict(code = "fail", message = "无权删除")
    
    def load_data_list(self):
        user_name = xauth.current_name()
        offset = xutils.get_argument("offset", 0, type = int)
        limit  = xutils.get_argument("limit", 20, type = int)
        data_list = TABLE.list_by_user(user_name, offset, limit, reverse = True)
        data_list = convert_data_list(data_list)
        self.writehtml(HTML, data_list = data_list)
    
    def handle(self, input):
        action  = xutils.get_argument("action", "")
        if action == "get_template":
            # 获取编辑对象
            return self.get_input_template()
        
        if action == "edit":
            # 编辑操作
            return self.edit_row()

        if action == "delete":
            # 删除操作
            return self.delete_row()
        
        # 加载数据列表
        return self.load_data_list()


if __name__ == "__main__":
    # 命令行中执行
    pass
