if (xnote.api.message === undefined) {
    xnote.api.message = {};
}


var MessageState = {};
// 优先用messageTag
MessageState.messageTag = "";
MessageState.tag = "";

if (xnote.state.message === undefined) {
    xnote.state.message = MessageState;
}

var MessageView = {};
MessageView.state = {};
MessageView.state.isEditDialog = false;
MessageView.listAjaxUrl = "/message/list";
xnote.action.message = MessageView;
xnote.message = MessageView;


MessageView.refreshList = function() {
    var self = this;
    function doRefreshMessageList(params) {
        console.log("doRefreshMessageList:", params);
        xnote.assert(typeof(params) == "object", "expect params to be object");
        xnote.assert(params.page, "params.page expected");
        xnote.assert(params.tag, "params.tag expected");

        params.format = "html";
        params.displayTag = getUrlParam("displayTag", "");

        console.log("[message] refresh messageList");
        
        xnote.http.get(MessageView.listAjaxUrl, params, function (resp) {
            // console.log(resp);
            $(".message-list").html(resp);
            
            // 更新代码块，添加高亮处理
            $(".message-list .code-block").each(function() {
                var $codeBlock = $(this);
                var $code = $codeBlock.find("code");
                var code = $code.text();
                
                // 提取语言信息（如果有）
                var lang = $codeBlock.data("lang");
                
                // 使用 xnote.editor.highlightCodeBlock 函数进行高亮处理
                var highlightedCode = xnote.editor.highlightCodeBlock(code, lang);
                
                // 更新代码块内容
                $codeBlock.html(highlightedCode);
            });
        });
    }

    function getParamTag() {
        var argTag = xnote.getUrlParam("tag", "");
        if (argTag != "") {
            return argTag;
        }
        return MessageState.messageTag;
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

    // 刷新列表
    var params = getUrlParams();

    params.tag  = getParamTag();
    params.page = getParamPage();
    params.key = getParamKey();

    doRefreshMessageList(params);
}

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

MessageView.insertTagToInputBox = function (newTopic) {
    var oldText = this.getInputText();
    var self = this;
    
    if (oldText == "") {
        self.setInputText(newTopic);
        return;
    }

    xnote.http.post("/message/add_tag", {content:oldText, new_tag:newTopic}, function(resp) {
        if (resp.success) {
            self.setInputText(resp.data);
        } else {
            xnote.alert(resp.message);
        }
    });
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
    xnote.http.get("/message/edit_dialog", params, function (html) {
        var layerId = xnote.openDialog("编辑", html);
        MessageView.closeEdit = function () {
            // console.log("close dialog:", layerId);
            xnote.closeDialog(layerId);
            MessageView.state.isEditDialog = false;
        };
    });
};

// 展示选择标签对话框
MessageView.showTopicDialog = function (target) {
    xnote.http.get("/message/tag/search_dialog?pagesize=100&page=1&key=&tag=key", function (html) {
        var dialogId = xnote.openDialog("选择标签", html);
        MessageView.closeTopicDiloag = function () {
            xnote.closeDialog(dialogId);
        }
    });
};

MessageView.buildFiles = function() {
    var result = [];
    $(".upload-img").each(function (index, ele) {
        var src = $(ele).attr("data-src");
        result.push(src);
    });
    return result;
}


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
    
    params.files = MessageView.buildFiles();
    var self = this;

    xnote.http.post("/message/update", params, function (resp) {
        if (resp.code == "success") {
            xnote.toast("更新成功");
            self.closeEdit();
            // self.refreshList();
            window.location.reload();
        } else {
            xnote.alert("更新失败:" + resp.message);
        }
    });
};

MessageView.createMessage = function (target) {
    var createTag = $(target).attr("data-create-tag");
    var defaultContent = $(target).attr("data-default-content");
    var content = $(".input-box").val();
    var date = getUrlParam("date");
    var params = {content:content, tag: createTag, date: date};
    params.files = MessageView.buildFiles();

    xnote.http.post("/message/save", 
        params,
        function (respText) {
            var data = respText;
            if (data.success) {
                $(".input-box").val(defaultContent);
                $(".input-box")[0].style.height = "52px";
                // 刷新列表
                // MessageView.refreshList();
                window.location.reload();
            } else {
                xnote.alert(data.message);
            }
    });
}

// 基于标签创建新记录
MessageView.createMessageOnTag = function(target) {
    var self = this;
    self.state.isEditDialog = true;
    var keyword = $(target).attr("data-keyword");
    var tag = $(target).attr("data-tag");
    var title = $(target).attr("data-title");
    var params = {
        "tag": tag,
        "keyword": keyword
    };
    xnote.http.get("/message/create_dialog", params, function (html) {
        var layerId = xnote.openDialog(title, html);
        self.closeEdit = function () {
            // console.log("close dialog:", layerId);
            xnote.closeDialog(layerId);
            self.state.isEditDialog = false;
        };
    })
};

MessageView.upload = function () {
    // 上传文件
    console.log("select file button click");
    $("#baseFilePicker").click();
};


MessageView.touchTopic = function(topic) {
    var params = {"key": topic};
    xnote.http.post("/message/touch", params, function (resp) {
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
    this.insertTagToInputBox(topicText);
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
    xnote.promptTextarea("备注", "", function (inputText) {
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

/**
 * 执行删除备注动作
 * @param {req.id} msgId
 * @param {req.time} time
 */
MessageView.doDeleteComment = function (req) {
    var msgId = req.id;
    xnote.http.post("/message/comment/delete", req, function (resp) {
        if (resp.success) {
            xnote.toast("删除备注成功");
            MessageView.refreshCommentList(msgId);
        } else {
            xnote.toast(resp.message);
        }
    });
}

MessageView.deleteComment = function (target) {
    var msgId = $(target).attr("data-id");
    var time = $(target).attr("data-time");
    var req = {};
    req.id = msgId;
    req.time = time;
    console.log("deleteComment req:", req);
    xnote.confirm("确认删除备注吗?", function (result) {
        MessageView.doDeleteComment(req);
    });
}

MessageView.refreshCommentList = function(msgId) {
    var req = {};
    req.id = msgId;
    console.log("listComments req:", req);
    xnote.http.post("/message/comment/list", req, function (resp_html) {
        $("#listCommentDialog").html(resp_html);
    });
}

MessageView.showAllComments = function(target, selector) {
    xnote.showDialog("查看备注", '<div id="listCommentDialog"></div>', ["关闭"]);
    this.refreshCommentList($(target).attr("data-id"))
}

MessageView.updateMessageTag = function(id, tag) {
    xnote.http.post("/message/update_first_tag", { id: id, tag: tag }, function (resp) {
        if (resp.success) {
            xnote.toast("更新状态成功");
            xnote.fire("message.updated");
        } else {
            xnote.alert(resp.message);
        }
    });
}

// 重新打开任务
MessageView.reopen = function (target) {
    // 标记为完成
    var id = $(target).attr("data-id");
    this.updateMessageTag(id, "task");
};

// 删除message
MessageView.deleteMessage = function(target) {
    var id = $(target).attr("data-id");
    var content = $(target).attr("data-content");

    xnote.confirm("确认删除[" + content + "]吗?", function (result) {
        xnote.http.post("/message/delete", { id: id }, function (resp) {
            if (resp.code == "success") {
                // MessageView.refreshList();
                window.location.reload();
            } else {
                xnote.alert(resp.message);
            }
        });
    });
};

MessageView.handleTopicSearchKeyUp = function (e) {
    console.log(e);
    var inputText = $(e.target).val();
    MessageView.searchTopic(inputText);
}


MessageView.removeUploadedImg = function(target) {
    var targetId = $(target).attr("data-id");
    $("#" + targetId).remove();
}


MessageView.renderUploadedImg = function(link) {
    var targetSelector = "";
    if (MessageView.state.isEditDialog) {
        targetSelector = "#messageEditImgRow";
    } else {
        targetSelector = "#messageImgRow";
    }
    var id = "upload_" + xnote.createNewId();
    var div = $("<div>").addClass("upload-img-div").attr("id", id);
    var img = $("<img>").addClass("upload-img");
    img.attr("src", link + "?mode=thumbnail");
    img.attr("data-src", link);
    var deleteLink = $("<a>").text("删除").attr("data-id", id).attr("onclick", "xnote.message.removeUploadedImg(this)");
    div.append(img).append(deleteLink);
    $(targetSelector).append(div);
}


$("body").on("focus", ".msg-edit-box textarea", function (e) {
    if (xnote.device.isIphone) {
        $(".layui-layer-content").height("50%");
    }
})

$(function () {
    // 需要前置设置这两个参数
    // xnote.state.message.messageTag = "{{message_tag}}";
    // xnote.state.message.tag = "{{tag}}";

    function getParamTag() {
        var tag = MessageState.messageTag;
        if (tag != "") {
            return tag;
        }
        return MessageState.tag;
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

    function onMessageRefresh() {
        var params = getUrlParams();

        params.tag  = getParamTag();
        params.page = getParamPage();
        params.key = getParamKey();

        window.doRefreshMessageList(params);
    }

    function onMessageCreated() {
        onMessageRefresh();
    }

    xnote.on("message.updated", onMessageRefresh);
    xnote.on("message.created", onMessageCreated);

    // 定义刷新消息列表函数
    xnote.setExtFunc("message.refreshMessageList", onMessageRefresh);
});



$(function() {
    // 上传文件
    // baseFilePicker定义在 base.html 文件里面
    xnote.createUploaderEx({
        fileSelector: "#baseFilePicker",
        chunked: false,
        successFn: function (resp) {
            console.log("文件上传成功", resp);
            xnote.message.renderUploadedImg(resp.webpath);
        },
        fixOrientation: true,
        fileName: "auto"
    });

    // 剪切板粘贴上传
    $("body").on("paste", ".edit-box,.input-box", function (e) {
        var filePrefix = "";
        xnote.requestUploadByClip(e, filePrefix, function (resp) {
            console.log("剪贴板上传成功", resp);
            xnote.message.renderUploadedImg(resp.webpath);
        });
    });

});
