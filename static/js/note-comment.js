
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
