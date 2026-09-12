/**
 * 表单插件的JS脚本，待稳定后启用
 * @author xupingmao
 * @since 2021/09/04 23:56:44
 * @modified 2021/09/05 00:03:44
 * @filename plugin.form.js
 */

$(function(){
    // 编辑事件处理
    $(".x-form-edit-btn").click(function (event) {
        var rowKey  = $(event.target).attr("data-key");
        $.get("?action=get_template", {key: rowKey}, function(resp) {
            var buttons = ["确认", "取消"];
            var functions = [function (index, layero) {
                var content = $("[name=content]").val();
                var params = {content: content, key: rowKey};
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
    $(".x-form-delete-btn").click(function (event) {
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
});