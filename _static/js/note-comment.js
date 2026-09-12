
xnote.comment.editIndex = null;
xnote.comment.replyIndex = null;

xnote.comment.removeUploadedImg = function(target) {
    var targetId = $(target).attr("data-id");
    $("#" + targetId).remove();
}

// 构建已上传文件列表
xnote.comment.buildFiles = function(imgRowSelector) {
    var result = [];
    $(imgRowSelector + " .upload-img").each(function (index, ele) {
        var src = $(ele).attr("data-src");
        result.push(src);
    });
    return result;
}

// 初始化评论编辑对话框
xnote.comment.initEditDialog = function() {
    // laydate 渲染
    if (typeof laydate !== 'undefined') {
        laydate.render({
            elem: '#commentDate',
            value: $("#commentDate").attr("data-value") || ""
        });
    }
    
    // 附件按钮点击
    $(".attachment-btn").click(function (e) {
        $("#commentFilePicker2").click();
    });

    // 文件上传器
    xnote.createUploaderEx({
        fileSelector: "#commentFilePicker2",
        chunked: false,
        successFn: function (resp) {
            console.log("文件上传成功", resp);
            xnote.comment.renderUploadedImg(resp.webpath, "#commentEditImgRow");
        },
        fixOrientation: true
    });

    // 通过剪切板上传
    $("#commentUpdateContent").on("paste", function (e) {
        xnote.requestUploadByClip(e, "msg", function (respJson) {
            console.log(respJson);
            xnote.comment.renderUploadedImg(respJson.webpath, "#commentEditImgRow");
        });
    });
}

// 更新评论
xnote.comment.updateComment = function() {
    var params = {};
    params.p = "update";
    params.comment_id = $("#commentUpdateContent").attr("data-comment-id");
    params.content = $("#commentUpdateContent").val();
    params.date = $("#commentDate").val();
    params.files = xnote.comment.buildFiles("#commentEditImgRow");
    params.version = $("#commentUpdateContent").attr("data-version");
    xnote.http.post("/note/comment", params, function (resp) {
        if (resp.success) {
            xnote.toast("更新成功");
            xnote.fire("comment.refresh");
            if (xnote.comment.editIndex != null) {
                xnote.closeDialog(xnote.comment.editIndex);
            }
        } else {
            xnote.alert(resp.message);
        }
    });
}


xnote.comment.renderUploadedImg = function(link, targetSelector) {
    var id = "upload_" + xnote.createNewId();
    var div = $("<div>").addClass("upload-img-div").attr("id", id);
    var img = $("<img>").addClass("upload-img");
    img.attr("src", link + "?mode=thumbnail");
    img.attr("data-src", link);
    var deleteLink = $("<a>").text("删除").attr("data-id", id).attr("onclick", "xnote.comment.removeUploadedImg(this)");
    div.append(img).append(deleteLink);
    $(targetSelector).append(div);
}

// 打开编辑对话框
xnote.comment.openEditDialog = function(element) {
    var id = $(element).attr("data-id");
    xnote.http.get("/note/comment?p=edit&comment_id=" + id, function (resp) {
        xnote.comment.editIndex = xnote.showDialog("编辑", resp);
    });
}

// 删除评论
xnote.comment.deleteComment =function (element) {
    var id = $(element).attr("data-id");
    var content = $(element).attr("data-content");
    xnote.confirm("确定删除`" + content + "`?", function (conf) {
        if (conf) {
            xnote.http.post("/note/comment/delete", { comment_id: id }, function (resp) {
                refreshComments();
            });
        }
    });
};

// 删除回复
xnote.comment.deleteReply = function(element) {
    var id = $(element).attr("data-id");
    var content = $(element).attr("data-content");
    xnote.confirm("确定删除回复`" + content + "`?", function (conf) {
        if (conf) {
            xnote.http.post("/note/comment/delete", { comment_id: id }, function (resp) {
                if (resp.success) {
                    xnote.fire("comment.refresh");
                    xnote.comment.refreshReplyList();
                } else {
                    xnote.alert(resp.message);
                }
            });
        }
    });
};


// 打开回复对话框
xnote.comment.openReplyDialog = function(element) {
    var $ele = $(element);
    var commentId = $ele.data("id");
    var user = $ele.data("user");
    var userId = $ele.data("user-id");
    var noteId = $ele.data("note-id");
    
    var url = "/note/comment/reply_dialog?note_id=" + noteId 
            + "&parent_comment_id=" + commentId
            + "&ref_comment_id=" + commentId
            + "&ref_user_id=" + userId
            + "&ref_user=" + encodeURIComponent(user);
    
    xnote.http.get(url, function (resp) {
        xnote.comment.replyIndex = xnote.showDialog("回复 " + user, resp);
    });
};

// 查看回复（调用openReplyDialog）
xnote.comment.viewReplies = function(element) {
    var $ele = $(element);
    var commentId = $ele.data("id");
    var user = $ele.data("user");
    var userId = $ele.data("user-id");
    var noteId = $ele.data("note-id");
    
    var url = "/note/comment/reply_dialog?note_id=" + noteId 
            + "&parent_comment_id=" + commentId
            + "&ref_comment_id=" + commentId
            + "&ref_user_id=" + userId
            + "&ref_user=" + encodeURIComponent(user);
    
    xnote.http.get(url, function (resp) {
        xnote.comment.replyIndex = xnote.showDialog("回复 " + user, resp);
    });
};

// 初始化评论回复对话框
xnote.comment.initReplyDialog = function(context) {
    xnote.comment.replyContext = context;
    
    // 加载回复列表
    xnote.comment.loadReplyList = function() {
        xnote.http.get("/note/comment/reply_list", {
            note_id: xnote.comment.replyContext.note_id,
            parent_comment_id: xnote.comment.replyContext.parent_comment_id
        }, function(resp) {
            $("#commentReplyList").html(resp);
        });
    };
    
    // 刷新回复列表
    xnote.comment.refreshReplyList = function() {
        xnote.comment.loadReplyList();
    };
    
    // 点击回复按钮
    xnote.comment.replyTo = function(element) {
        var user = $(element).data("user");
        var userId = $(element).data("user-id");
        var commentId = $(element).data("id");
        xnote.comment.replyContext.ref_comment_id = commentId;
        xnote.comment.replyContext.ref_user_id = userId;
        xnote.comment.replyContext.ref_user = user;
        $("#commentReplyContent").attr("placeholder", "回复 @" + user + ":").focus();
    };
    
    // 提交回复
    xnote.comment.submitReply = function() {
        var content = $("#commentReplyContent").val();
        if (content == "") {
            xnote.alert("回复内容不能为空");
            return;
        }
        
        xnote.http.post("/note/comment/save", {
            note_id: xnote.comment.replyContext.note_id,
            content: content,
            parent_comment_id: xnote.comment.replyContext.parent_comment_id,
            ref_comment_id: xnote.comment.replyContext.ref_comment_id,
            ref_user_id: xnote.comment.replyContext.ref_user_id
        }, function(resp) {
            if (resp.success) {
                xnote.toast("回复成功");
                $("#commentReplyContent").val("");
                // 重置ref信息
                xnote.comment.replyContext.ref_comment_id = xnote.comment.replyContext.parent_comment_id;
                xnote.comment.replyContext.ref_user_id = xnote.comment.replyContext.original_ref_user_id;
                xnote.comment.replyContext.ref_user = xnote.comment.replyContext.original_ref_user;
                $("#commentReplyContent").attr("placeholder", "写下你的回复...");
                // 刷新回复列表
                xnote.comment.loadReplyList();
                xnote.fire("comment.refresh");
            } else {
                xnote.alert(resp.message);
            }
        });
    };
    
    // 初始化附件上传
    $(".attachment-btn").click(function (e) {
        $("#commentReplyFilePicker").click();
    });

    xnote.createUploaderEx({
        fileSelector: "#commentReplyFilePicker",
        chunked: false,
        successFn: function (resp) {
            console.log("文件上传成功", resp);
            xnote.comment.renderUploadedImg(resp.webpath, "#commentReplyImgRow");
        },
        fixOrientation: true
    });
    
    // 初始化时加载回复列表
    xnote.comment.loadReplyList();
};
