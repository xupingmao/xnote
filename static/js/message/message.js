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

        xnote.http.get("/message/date", params,function (respText) {
            $(".message-list").html(respText);
        });
    };

    function doRefreshMessageList(params) {
        xnote.assert(typeof(params) == "object", "expect params to be object");
        xnote.assert(params.page, "params.page expected");
        xnote.assert(params.tag, "params.tag expected");

        params.format = "html";
        params.displayTag = getUrlParam("displayTag", "");

        xnote.http.get("/message/list", params, function (resp) {
            // console.log(resp);
            $(".message-list").html(resp);
        });
    }

    function getParamTag() {
        return xnote.getUrlParam("tag");
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
        var filePrefix = "";
        xnote.requestUploadByClip(e, filePrefix, function (resp) {
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

// 编辑随手记
MessageView.edit = function (target) {
    MessageView.state.isEditDialog = true;

    var id = $(target).attr("data-id");
    // 打开编辑器
    var params = {
        id: id
    };
    xnote.http.get("/message/detail", params, function (resp) {
        if (resp.code == "success") {
            var html = $("#msg-edit-tpl").render({
                detail: resp.data,
                submitBtnText: "更新"
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
    });
};

// 展示选择标签对话框
MessageView.showTopicDialog = function (target) {
    xnote.http.get("/message/list?pagesize=100&page=1&key=&tag=key", function (resp) {
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
    });
};

MessageView.saveMessage = function (target) {
    // 保存信息
    var id = $("#messageEditId").val();
    var content = $("#messageEditContent").val();
    var tag = $("#messageEditTag").val();

    var params = {
        id: id,
        content: content,
        tag: tag
    }

    var self = this;

    xnote.http.post("/message/update", params, function (resp) {
        if (resp.code == "success") {
            xnote.toast("更新成功");
            self.closeEdit();
            self.refreshList();
        } else {
            xnote.alert("更新失败:" + resp.message);
        }
    });
};

// 基于标签创建新记录
MessageView.createMessageOnTag = function(target) {
    var self = this;
    self.state.isEditDialog = true;
    var keyword = $(target).attr("data-keyword");
    var tag = $(target).attr("data-tag");
    var title = $(target).attr("data-title");
    var html = $("#msg-edit-tpl").render({
        detail: {
            content: keyword + " ",
            tag: tag,
        },
        submitBtnText: "创建"
    });
    var layerId = xnote.openDialog(title, html);
    self.closeEdit = function () {
        // console.log("close dialog:", layerId);
        xnote.closeDialog(layerId);
        self.state.isEditDialog = false;
    };
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
    inputText = inputText.toLowerCase();
    var showCount = 0;
    var hasMatch = false;
    var inputTextTag = "#" + inputText + "#";

    $(".empty-item").hide();
    
    $(".topic-item").each(function (index, element) {
        var text = $(element).text().toLowerCase();
        if (text == inputTextTag) {
            hasMatch = true;
        }
        if (text.indexOf(inputText) < 0) {
            $(element).hide();
        } else {
            $(element).show();
            showCount++;
        }
    });

    if (!hasMatch) {
        var showText = "";
        if (inputText == "") {
            showText = "#请输入标签#";
        } else {
            showText = "#" + inputText + "#";
        }
        $(".empty-item").text(showText).show();
    }
}

MessageView.markTagLevel = function (e) {
    var params = {};
    params.keyword = $(".keyword-span").text();
    params.action = $(e.target).attr("data-action");

    xnote.http.post("/message/keyword", params, function (resp) {
        if (resp.code == "success") {
            xnote.toast("标记成功");
            window.location.reload();
        } else {
            xnote.alert("标记失败:" + resp.message);
        }
    });
}

MessageView.createComment = function (target) {
    var id = $(target).attr("data-id");
    if (id == "") {
        xnote.toast("id不能为空");
        return;
    }
    xnote.prompt("备注", "", function (inputText) {
        var req = {};
        req.id = id;
        req.content = inputText;
        xnote.http.post("/message/comment/create", req, function (resp) {
            if (resp.success) {
                xnote.toast("备注成功");
                window.location.reload();
            } else {
                xnote.toast(resp.message);
            }
        });
    });
}

MessageView.deleteComment = function (target) {
    var id = $(target).attr("data-id");
    var time = $(target).attr("data-time");
    var req = {};
    req.id = id;
    req.time = time;
    console.log("deleteComment req:", req);
    xnote.http.post("/message/comment/delete", req, function (resp) {
        if (resp.success) {
            xnote.toast("删除备注成功");
            MessageView.refreshCommentList(id, "#msgCommentListTpl");
        } else {
            xnote.toast(resp.message);
        }
    });
}

MessageView.refreshCommentList = function(id, selector) {
    var req = {};
    req.id = id;
    console.log("listComments req:", req);
    xnote.http.post("/message/comment/list", req, function (resp) {
        if (resp.success) {
            var html = $(selector).render({
                commentList: resp.data,
                msgId: id
            });
            $("#listCommentDialog").html(html);
        } else {
            xnote.toast(resp.message);
        }
    });
}

MessageView.showAllComments = function(target, selector) {
    xnote.showDialog("查看备注", '<div id="listCommentDialog"></div>', ["关闭"]);
    this.refreshCommentList($(target).attr("data-id"), selector);
}

MessageView.updateMessageTag = function(id, tag) {
    xnote.http.post("/message/tag", { id: id, tag: tag }, function (resp) {
        if (resp.code == "success") {
            xnote.toast("更新状态成功");
            xnote.fire("message.updated");
        } else {
            alert(resp.message);
        }
    });
}

// 重新打开任务
MessageView.reopen = function (target) {
    // 标记为完成
    var id = $(target).attr("data-id");
    this.updateMessageTag(id, "task");
};

$("body").on("keyup", ".nav-search-input", function (e) {
    console.log(e);
    var inputText = $(e.target).val();
    MessageView.searchTopic(inputText);
});

$("body").on("focus", ".msg-edit-box textarea", function (e) {
    if (xnote.device.isIphone) {
        $(".layui-layer-content").height("50%");
    }
})