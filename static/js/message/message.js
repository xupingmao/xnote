if (xnote.api.message === undefined) {
    xnote.api.message = {};
}

if (xnote.state.message === undefined) {
    xnote.state.message = {};
}

var MessageView = {};
MessageView.state = {};
MessageView.state.isEditDialog = false;
xnote.action.message = MessageView;

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

    $("body").on("paste", ".edit-box,.input-box", function (e) {
        xnote.requestUploadByClip(e, "msg", function (resp) {
            console.log(resp);
            var webpath = "file://" + resp.webpath;
            xnote.action.message.updateInputBox(webpath);
        });
    });

});

// 更新输入框
MessageView.updateInputBox = function (webpath) {
    var oldText = this.getInputText();
    var leftPart = oldText;
    if (leftPart != "" && leftPart[leftPart.length-1]) {
        leftPart += "\n";
    }
    var newText = leftPart + webpath + "\n";
    this.setInputText(newText);
}

MessageView.getInputText = function () {
    if (this.state.isEditDialog) {
        return $(".edit-box").val();
    } else {
        return $(".input-box").val();
    }
}

MessageView.setInputText = function (text) {
    if (this.state.isEditDialog) {
        $(".edit-box").val(text);
    } else {
        $(".input-box").val(text);
    }
}

// 更新输入框
MessageView.insertBeforeInputBox = function (text) {
    var oldText = this.getInputText();
    var newText = text + " " + oldText;
    this.setInputText(newText);
}

MessageView.closeEdit = function () {
    // 打开编辑框的时候会重写这个方法
};

MessageView.closeTopicDiloag = function () {
    // 关闭
}

MessageView.edit = function (target) {
    MessageView.state.isEditDialog = true;

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
            MessageView.closeEdit = function () {
                // console.log("close dialog:", layerId);
                xnote.closeDialog(layerId);
                MessageView.state.isEditDialog = false;
            };
        } else {
            xnote.alert(resp.message);
        }
    }).fail(function (err) {
        xnote.alert("接口失败:" + err);
    });
};

MessageView.showTopicDialog = function (target) {
    $.get("/message/list?pagesize=100&page=1&key=&tag=key", function (resp) {
        if (resp.code != "success") {
            xnote.alert(resp.message);
        } else {
            // 选择标签
            var html = $("#msg-tag-list-tpl").render({
                itemList: resp.data
            });
            var dialogId = xnote.openDialog("选择标签", html);
            MessageView.closeTopicDiloag = function () {
                xnote.closeDialog(dialogId);
            }
        }
    }).fail(function (err) {
        xnote.alert("调用接口失败, err=" + err);
    });
};

MessageView.saveMessage = function (target) {
    // 保存信息
    var id = $("#messageEditId").val();
    var content = $("#messageEditContent").val();

    var params = {
        id: id,
        content: content,
    }

    var self = this;

    $.post("/message/update", params, function (resp) {
        if (resp.code == "success") {
            xnote.toast("更新成功");
            self.closeEdit();
            self.refreshList();
        } else {
            xnote.alert("更新失败:" + resp.message);
        }
    }).fail(function (e) {
        console.error(e);
        xnote.alert("系统繁忙，请稍后重试");
    });
};

MessageView.upload = function () {
    // 上传文件
    console.log("select file button click");
    $("#filePicker").click();
};


MessageView.touchTopic = function(topic) {
    var params = {"key": topic};
    $.post("/message/touch", params, function (resp) {
        console.log(resp);
    }).fail(function (error) {
        console.error(error);
    })
}

// 创建话题标签
MessageView.createTopicText = function(topic) {
    if (topic.Get(0) == '#' && topic.Get(-1) == '#') {
        return topic;
    }

    if (topic.Get(0) == '《' && topic.Get(-1) == '》') {
        return topic;
    }
    
    return '#' + topic + '#';
}


MessageView.selectTopic = function (target) {
    var topic = $(target).text();

    // 将话题置顶
    this.touchTopic(topic);

    var topicText = this.createTopicText(topic);

    this.closeTopicDiloag();

    // 发布选择消息的事件
    this.insertBeforeInputBox(topicText);
}

// 搜索话题标签
MessageView.searchTopic = function(inputText) {
    var showCount = 0;

    $(".empty-item").hide();
    
    $(".topic-item").each(function (index, element) {
        var text = $(element).text();
        if (text.indexOf(inputText) < 0) {
            $(element).hide();
        } else {
            $(element).show();
            showCount++;
        }
    });

    if (showCount == 0) {
        $(".empty-item").show();
    }
}

$("body").on("keyup", ".nav-search-input", function (e) {
    console.log(e);
    var inputText = $(e.target).val();
    MessageView.searchTopic(inputText);
});
