/*
 * @Author       : xupingmao
 * @email        : 578749341@qq.com
 * @Date         : 2023-11-18 22:14:37
 * @LastEditors  : xupingmao
 * @LastEditTime : 2023-11-18 22:47:29
 * @FilePath     : /xnote/static/js/admin.js
 * @Description  : 后台管理脚本
 */
var AdminView = {}
xnote.admin = AdminView;

// 查看主数据
AdminView.viewMainRecord = function (target) {
    var url = $(target).attr("data-url");
    xnote.http.get(url, function (resp) {
        if (resp.success) {
            xnote.showTextDialog("主数据详情", resp.data, ["确定"]);
        } else {
            xnote.toast(resp.message);
        }
    })
}