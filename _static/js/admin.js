/*
 * @Author       : xupingmao
 * @email        : 578749341@qq.com
 * @Date         : 2023-11-18 22:14:37
 * @LastEditors  : xupingmao
 * @LastEditTime : 2024-05-03 14:55:44
 * @FilePath     : /xnote/_static/js/admin.js
 * @Description  : 后台管理脚本
 */

/**
 * @typedef {import('./xnote-ui/docs.js')}
 */
var AdminView = {};
xnote.admin = AdminView;

// 查看主数据
AdminView.viewMainRecord = function (target) {
    var url = $(target).attr("data-url");
    xnote.http.get(url, function (resp) {
        if (resp.success) {
            xnote.showTextDialog("主数据详情", resp.data);
        } else {
            xnote.toast(resp.message);
        }
    })
}

// 安装python库
AdminView.installPythonLib = function (target) {
    var libName = $(target).attr("data-lib-name");
    xnote.confirm("确认要安装" + libName + "吗?", function () {
        var params = {
            lib_name: libName
        };
        xnote.http.post("/system/install_python_lib", params, function (resp) {
            if (resp.success) {
                xnote.toast("安装成功");
                window.location.reload();
            } else {
                xnote.alert("安装失败:" + resp.message);
            }
        });
    });
};

AdminView.doRestart = function () {
    xnote.toast("重启中，请等待2-5分钟...");
    var runtimeId = $("input[name=runtimeId]").val();
    var checkInterval = 500;

    var checkSystemStatus = function() {
        xnote.http.internalPost("/system/reload?runtime_id=" + runtimeId, function (resp) {
            console.log(resp)
            if (resp.success) {
                xnote.toast("重启成功!");
                window.location.reload();                
            } else {
                setTimeout(checkSystemStatus, checkInterval)
            }
        }).fail(function (err) {
            console.error("checkSystemStatus failed, wait to retry", err);
            setTimeout(checkSystemStatus, checkInterval);
        })
    };

    var loadingIndex = layer.load(1);
    checkSystemStatus();
};

/**
 * 处理重启命令
 */
AdminView.onRestart = function () {
    xnote.confirm("确定重启吗?", function () {
        AdminView.doRestart();
    })
};

AdminView.onUpgrade = function() {
    var doUpgrade = function() {
        xnote.http.post("/system/pull_code", function (resp) {
            if (resp.success) {
                AdminView.doRestart();
            } else {
                xnote.alert(resp.message);
            }
        })
    }

    xnote.confirm("确定升级系统吗?", function () {
        doUpgrade();
    });
};
