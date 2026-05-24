
xnote.comment.removeUploadedImg = function(target) {
    var targetId = $(target).attr("data-id");
    $("#" + targetId).remove();
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
        editIndex = xnote.showDialog("编辑", resp);
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
        xnote.showDialog("回复 " + user, resp);
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
        xnote.showDialog("回复 " + user, resp);
    });
};
