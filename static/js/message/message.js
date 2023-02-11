
if (xnote.action.message === undefined) {
    xnote.action.message = {};
}

if (xnote.api.message === undefined) {
    xnote.api.message = {};
}

if (xnote.state.message === undefined) {
    xnote.state.message = {};
}

$(function() {
    var LAST_DATE;

    function getCurrentPage() {
        var page = getUrlParam("page");
        if (page == undefined) {
            return 1;
        } else {
            return parseInt(page);
        }
    }

    function refreshMessageList(date) {
        LAST_DATE = date;
        var params = {
            date: date,
            page: getCurrentPage()
        };

        $.get("/message/date", params,function (respText) {
            $(".message-list").html(respText);
        }).fail(function (e) {
            console.error(e);
            xnote.alert("调用接口失败");
        });
    };

    function doRefreshMessageList(params) {
        xnote.assert(typeof(params) == "object", "expect params to be object");
        xnote.assert(params.page, "params.page expected");
        xnote.assert(params.tag, "params.tag expected");

        params.format = "html";
        params.displayTag = getUrlParam("displayTag", "");

        $.get("/message/list", params, function (resp) {
            // console.log(resp);
            $(".message-list").html(resp);
        }).fail(function (e) {
            console.error(e);
            xnote.alert("调用接口失败，请稍后重试");
        });
    }

    function getParamTag() {
        var tag = xnote.state.message.messageTag;
        if (tag != "") {
            return tag;
        }
        return xnote.state.message.tag;
    }

    function getParamPage() {
        var page = getUrlParam("page");
        if (page == undefined) {
            return 1;
        } else {
            return page;
        }
    }

    function getParamKey() {
        // getUrlParam 获取参数空格会被处理成`+`
        // return getUrlParam("key", "");
        return $(".msg-search-key").val();
    }

    xnote.action.message.refreshList = function () {
        // 刷新列表
        var params = getUrlParams();

        params.tag  = getParamTag();
        params.page = getParamPage();
        params.key = getParamKey();

        doRefreshMessageList(params);
    };

    // 上传文件
    xnote.createUploaderEx({
        fileSelector: "#filePicker",
        chunked: false,
        successFn: function (resp) {
            console.log("文件上传成功", resp);
            var webpath = "file://" + resp.webpath
            xnote.action.message.updateInputBox(webpath);
        },
        fixOrientation: true
    });

    // 通过剪切板上传
    $(".input-box").on("paste", function (e) {
        xnote.requestUploadByClip(e, "msg", function (resp) {
            console.log(resp);
            var webpath = "file://" + resp.webpath;
            xnote.action.message.updateInputBox(webpath);
        });
    });

});

// 更新输入框
xnote.action.message.updateInputBox = function (webpath) {
    var oldText = $(".input-box").val();
    var leftPart = oldText;
    if (leftPart != "" && leftPart[leftPart.length-1]) {
        leftPart += "\n";
    }
    var newText = leftPart + webpath + "\n";
    $(".input-box").val(newText);
}

xnote.action.message.closeEdit = function () {
    // 打开编辑框的时候会重写这个方法
};

xnote.action.message.edit = function (target) {
    var id = $(target).attr("data-id");
    // 打开编辑器
    var params = {
        id: id
    };
    $.get("/message/detail", params, function (resp) {
        if (resp.code == "success") {
            var html = $("#msg-edit-tpl").render({
                detail: resp.data
            });
            var layerId = xnote.openDialog("编辑", html);
            xnote.action.message.closeEdit = function () {
                // console.log("close dialog:", layerId);
                xnote.closeDialog(layerId);
            };
        } else {
            xnote.alert(resp.message);
        }
    }).fail(function (err) {
        xnote.alert("接口失败:" + err);
    });
};

xnote.action.message.selectTopic = function (target) {
    // 选择标签
    xnote.openDialog("选择标签", html);
};

xnote.action.message.saveMessage = function (target) {
    // 保存信息
    var id = $("#messageEditId").val();
    var content = $("#messageEditContent").val();

    var params = {
        id: id,
        content: content
    }

    $.post("/message/update", params, function (resp) {
        if (resp.code == "success") {
            xnote.toast("更新成功");
            xnote.action.message.closeEdit();
            xnote.action.message.refreshList();
        } else {
            xnote.alert("更新失败:" + resp.message);
        }
    }).fail(function (e) {
        console.error(e);
        xnote.alert("系统繁忙，请稍后重试");
    });
};

xnote.action.message.upload = function () {
    // 上传文件
    console.log("select file button click");
    $("#filePicker").click();
};
