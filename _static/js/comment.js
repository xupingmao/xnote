/**
 * 评论功能（笔记 / 待办 / 清单共用）
 * 合并自原 comment.html 内联脚本 与 note-comment.js,
 * 通过容器上的 data-* 属性区分 target_id / save_url / create_type,
 * 不再依赖模板内联脚本。
 * @author xupingmao
 * @since 2026/09/18
 */

if (window.xnote === undefined) {
    var xnote = {};
}
xnote.comment = xnote.comment || {};

xnote.comment.editIndex = null;
xnote.comment.replyIndex = null;

// 删除已上传的图片
xnote.comment.removeUploadedImg = function (target) {
    var targetId = $(target).attr("data-id");
    $("#" + targetId).remove();
};

// 构建已上传文件列表
xnote.comment.buildFiles = function (imgRowSelector) {
    var result = [];
    $(imgRowSelector + " .upload-img").each(function (index, ele) {
        var src = $(ele).attr("data-src");
        result.push(src);
    });
    return result;
};

// 渲染上传成功的图片（追加到指定容器）
xnote.comment.renderUploadedImg = function (link, targetSelector) {
    var id = "upload_" + xnote.createNewId();
    var div = $("<div>").addClass("upload-img-div").attr("id", id);
    var img = $("<img>").addClass("upload-img");
    img.attr("src", link + "?mode=thumbnail");
    img.attr("data-src", link);
    var deleteLink = $("<a>").text("删除").attr("data-id", id).attr("onclick", "xnote.comment.removeUploadedImg(this)");
    div.append(img).append(deleteLink);
    $(targetSelector).append(div);
};

// 发表评论（保存按钮点击）
// btn 为保存按钮, 从最近的 .comment-box 容器读取 data-* 配置
xnote.comment.save = function (btn) {
    var box = $(btn).closest("#comment-box");
    var request = {};
    request.note_id = box.attr("data-target-id");
    request.content = $("#commentText").val();
    request.type = box.attr("data-create-type");
    request.files = xnote.comment.buildFiles("#commentImgRow");

    xnote.http.post(box.attr("data-save-url"), request, function (resp) {
        if (resp.success) {
            $("#commentText").val("");
            $("#commentImgRow").empty();
            if (resp.data) {
                xnote.executeCommands(resp.data);
            }
        } else {
            xnote.toast(resp.message);
        }
    });
};

// 读取当前评论排序（优先取激活的 x-tab, 其次 data-comment-order 兜底）
xnote.comment.getOrder = function (box) {
    var tabBox = box.find(".x-tab-box[data-tab-key='comment_order']");
    if (tabBox.length) {
        var active = tabBox.find(".x-tab.active");
        if (active.length) {
            return active.data("tab-value");
        }
        return tabBox.attr("data-tab-default") || "newest";
    }
    return box.attr("data-comment-order") || "latest";
};

// 通过独立的列表加载接口异步拉取评论列表 HTML 片段, 直接填充 #comments
// order / page 不传时从容器配置(激活 tab / data 属性)读取
xnote.comment.loadList = function (box, order, page) {
    box = $(box);
    order = order || xnote.comment.getOrder(box);
    // 评论分页参数使用 comment_page, 避免与页面自身的 page(如笔记分页)冲突
    page = page || box.attr("data-comment-page") || 1;

    var targetId = box.attr("data-target-id");
    var listUrl = box.attr("data-list-url");
    var listType = box.attr("data-list-type") || "note_id";
    var listDate = box.attr("data-list-date") || "";
    var showNote = box.attr("data-show-note") === "true";
    var showEdit = box.attr("data-show-edit") === "true";
    // type 用于后端区分笔记/待办(type="todo_task"), 不能用 target_id 区间判断
    // (笔记 id 为 13 位时间戳, 会超过旧的不相交区间, 区间判断会误判为待办)
    var commentType = box.attr("data-create-type") || "";

    var params = {
        note_id: targetId,
        list_type: listType,
        type: commentType,
        resp_type: "html",
        comment_order: order,
        comment_page: page,
        show_note: showNote ? "true" : "false",
        show_edit: showEdit ? "true" : "false",
        list_date: listDate
    };

    xnote.http.get(listUrl, params, function (resp) {
        box.find("#comments").html(resp);
    });
};


// 初始化评论编辑对话框
xnote.comment.initEditDialog = function () {
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
    if ($("#commentFilePicker2").length) {
        xnote.createUploaderEx({
            fileSelector: "#commentFilePicker2",
            chunked: false,
            successFn: function (resp) {
                xnote.comment.renderUploadedImg(resp.webpath, "#commentEditImgRow");
            },
            fixOrientation: true
        });
    }

    // 通过剪切板上传
    $("#commentUpdateContent").on("paste", function (e) {
        xnote.requestUploadByClip(e, "msg", function (respJson) {
            xnote.comment.renderUploadedImg(respJson.webpath, "#commentEditImgRow");
        });
    });
};

// 更新评论
xnote.comment.updateComment = function () {
    var params = {};
    params.comment_id = $("#commentUpdateContent").attr("data-comment-id");
    params.content = $("#commentUpdateContent").val();
    params.date = $("#commentDate").val();
    params.files = xnote.comment.buildFiles("#commentEditImgRow");
    params.version = $("#commentUpdateContent").attr("data-version");
    xnote.http.post("/comment/update", params, function (resp) {
        if (resp.success) {
            xnote.toast("更新成功");
            if (resp.data) {
                xnote.executeCommands(resp.data);
            }
            if (xnote.comment.editIndex != null) {
                xnote.closeDialog(xnote.comment.editIndex);
            }
        } else {
            xnote.alert(resp.message);
        }
    });
};

// 打开编辑对话框
xnote.comment.openEditDialog = function (element) {
    var id = $(element).attr("data-id");
    xnote.http.get("/comment/edit?comment_id=" + id, function (resp) {
        xnote.comment.editIndex = xnote.showDialog("编辑", resp);
    });
};

// 删除评论
xnote.comment.deleteComment = function (element) {
    var id = $(element).attr("data-id");
    var content = $(element).attr("data-content");
    var deleteUrl = $(element).attr("data-url") || "/comment/delete";
    xnote.confirm("确定删除`" + content + "`?", function (conf) {
        if (conf) {
            xnote.http.post(deleteUrl, { comment_id: id }, function (resp) {
                if (resp.success) {
                    if (resp.data) {
                        xnote.executeCommands(resp.data);
                    }
                } else {
                    xnote.alert(resp.message);
                }
            });
        }
    });
};

// 删除回复
xnote.comment.deleteReply = function (element) {
    var id = $(element).attr("data-id");
    var content = $(element).attr("data-content");
    xnote.confirm("确定删除回复`" + content + "`?", function (conf) {
        if (conf) {
            xnote.http.post("/comment/delete", { comment_id: id }, function (resp) {
                if (resp.success) {
                    // 后端返回 toast + 延迟 reload 命令, 整页刷新即可
                    if (resp.data) {
                        xnote.executeCommands(resp.data);
                    }
                } else {
                    xnote.alert(resp.message);
                }
            });
        }
    });
};

// 打开回复对话框
xnote.comment.openReplyDialog = function (element) {
    var $ele = $(element);
    var commentId = $ele.data("id");
    var user = $ele.data("user");
    var userId = $ele.data("user-id");
    var noteId = $ele.data("note-id");

    var url = "/comment/reply_dialog?note_id=" + noteId
        + "&parent_comment_id=" + commentId
        + "&ref_comment_id=" + commentId
        + "&ref_user_id=" + userId
        + "&ref_user=" + encodeURIComponent(user);

    xnote.http.get(url, function (resp) {
        xnote.comment.replyIndex = xnote.showDialog("回复 " + user, resp);
    });
};

// 查看回复（调用 openReplyDialog）
xnote.comment.viewReplies = function (element) {
    var $ele = $(element);
    var commentId = $ele.data("id");
    var user = $ele.data("user");
    var userId = $ele.data("user-id");
    var noteId = $ele.data("note-id");

    var url = "/comment/reply_dialog?note_id=" + noteId
        + "&parent_comment_id=" + commentId
        + "&ref_comment_id=" + commentId
        + "&ref_user_id=" + userId
        + "&ref_user=" + encodeURIComponent(user);

    xnote.http.get(url, function (resp) {
        xnote.comment.replyIndex = xnote.showDialog("回复 " + user, resp);
    });
};

// 初始化评论回复对话框
xnote.comment.initReplyDialog = function (context) {
    xnote.comment.replyContext = context;

    // 加载回复列表
    xnote.comment.loadReplyList = function () {
        xnote.http.get("/comment/reply_list", {
            note_id: xnote.comment.replyContext.note_id,
            parent_comment_id: xnote.comment.replyContext.parent_comment_id
        }, function (resp) {
            $("#commentReplyList").html(resp);
        });
    };

    // 刷新回复列表
    xnote.comment.refreshReplyList = function () {
        xnote.comment.loadReplyList();
    };

    // 点击回复按钮
    xnote.comment.replyTo = function (element) {
        var user = $(element).data("user");
        var userId = $(element).data("user-id");
        var commentId = $(element).data("id");
        xnote.comment.replyContext.ref_comment_id = commentId;
        xnote.comment.replyContext.ref_user_id = userId;
        xnote.comment.replyContext.ref_user = user;
        $("#commentReplyContent").attr("placeholder", "回复 @" + user + ":").focus();
    };

    // 提交回复
    xnote.comment.submitReply = function () {
        var content = $("#commentReplyContent").val();
        if (content == "") {
            xnote.alert("回复内容不能为空");
            return;
        }

        xnote.http.post("/comment/save", {
            note_id: xnote.comment.replyContext.note_id,
            content: content,
            parent_comment_id: xnote.comment.replyContext.parent_comment_id,
            ref_comment_id: xnote.comment.replyContext.ref_comment_id,
            ref_user_id: xnote.comment.replyContext.ref_user_id
        }, function (resp) {
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
                if (resp.data) {
                    xnote.executeCommands(resp.data);
                }
            } else {
                xnote.alert(resp.message);
            }
        });
    };

    // 初始化附件上传
    $(".attachment-btn").click(function (e) {
        $("#commentReplyFilePicker").click();
    });

    if ($("#commentReplyFilePicker").length) {
        xnote.createUploaderEx({
            fileSelector: "#commentReplyFilePicker",
            chunked: false,
            successFn: function (resp) {
                xnote.comment.renderUploadedImg(resp.webpath, "#commentReplyImgRow");
            },
            fixOrientation: true
        });
    }

    // 初始化时加载回复列表
    xnote.comment.loadReplyList();
};

// 置顶 / 取消置顶评论
xnote.note.pinComment = function (target, pinLevel) {
    var id = $(target).attr("data-id");
    var params = {
        comment_id: id,
        pin_level: pinLevel
    };
    xnote.http.post("/comment/update_pin_level", params, function (resp) {
        if (resp.success) {
            location.reload();
        } else {
            xnote.alert(resp.message);
        }
    });
};

// 评论创建框的初始化：文件选择 / 粘贴上传（页面加载时绑定一次）
$(function () {
    $("#commentFilePickerBtn").on("click", function (event) {
        $("#commentFilePicker").click();
    });

    if ($("#commentFilePicker").length) {
        xnote.createUploaderEx({
            fileSelector: "#commentFilePicker",
            chunked: false,
            successFn: function (resp) {
                xnote.comment.renderUploadedImg(resp.webpath, "#commentImgRow");
            },
            fixOrientation: true,
            fileName: "auto"
        });
    }

    $("#commentText").on("paste", function (e) {
        xnote.requestUploadByClip(e, "msg", function (respJson) {
            xnote.comment.renderUploadedImg(respJson.webpath, "#commentImgRow");
        });
    });

    xnote.on("comment.closeEditDialog", function () {
        layer.close(xnote.comment.editIndex);
    });

    $("textarea.auto-height").autoHeight();

    // 初始化时通过独立的列表加载接口异步加载评论列表（不再静态输出到页面）
    $(".comment-box").each(function () {
        xnote.comment.loadList(this);
    });
});
