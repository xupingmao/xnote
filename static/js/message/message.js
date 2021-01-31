$(function () {
    // 这个文件暂时未生效
    window.renderMessageImageBox = function() {
        $(".msg-img-box").each(function (i, e) {
            // $(e).width(200).height(200);
            var src = $(e).attr("data-src");
            var img = $("<img>").attr("src", src);
            $(e).append(img);
        });
    }
});