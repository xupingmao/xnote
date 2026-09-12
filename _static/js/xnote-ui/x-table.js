xnote.table.handleAction = function (target) {
    var url = $(target).attr("data-url");
    var title = $(target).attr("data-title");
    var xnoteDialogId = xnote.showIframeDialog(title, url, ["确认", "取消"]);
}

xnote.table.handleConfirmAction = function (target, event) {
    if (event instanceof Event) {
        event.preventDefault();
        event.stopPropagation();
    }
    var method = $(target).attr("data-method");
    var url = $(target).attr("data-url");
    var msg = $(target).attr("data-msg");
    var reloadUrl = $(target).attr("data-reload-url");
    var isAlert = $(target).attr("data-is-alert");

    if (method == "") {
        method = "GET";
    }
    xnote.confirm(msg, function () {
        xnote.http.ajax(method, url, "", function (resp) {
            console.log(resp);
            if (resp.success) {
                var msg = resp.message || "操作成功";
                if (isAlert) {
                    // alert 场景用于获取msg信息，不能刷新页面
                    xnote.alert(msg);
                } else {
                    xnote.toast(msg);
                    setTimeout(function() {
                        if (reloadUrl) {
                            window.location.href = reloadUrl;
                        } else {
                            window.location.reload();
                        }
                    }, 1000);
                }
            } else {
                if (isAlert) {
                    xnote.alert(resp.message);
                } else {
                    xnote.toast(resp.message);
                }
            }
        }); 
    });
}

xnote.table.handleEditForm = function (target) {
    var url = $(target).attr("data-url");
    var title = $(target).attr("data-title");

    xnote.http.get(url, function (respHtml) {
        var options = {};
        options.title = title;
        options.html = respHtml;
        xnote.showDialogEx(options);
    });
}

xnote.table.handleViewDetail = function (target) {
    // console.log("handleViewDetail", target);
    var detail = $(target).attr("data-detail");
    xnote.showTextDialog("查看详情", detail);
}

xnote.table.handleViewImage = function (target) {
    // 点击缩略图查看原图
    var origin = $(target).attr("data-origin") || $(target).attr("src");
    var html = '<div style="text-align:center;padding:10px;">'
        + '<img class="xnote-image-preview" src="' + origin + '"/></div>';
    var options = {};
    options.title = "查看原图";
    options.html = html;
    options.area = xnote.getDialogAreaLarge();
    options.buttons = "关闭";
    options.functions = [function (index) {
        layer.close(index);
    }];
    xnote.showDialogEx(options);
}
