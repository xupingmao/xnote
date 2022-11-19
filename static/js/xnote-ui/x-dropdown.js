/** 下拉组件
 * @since 2020/01/11
 * @modified 2020/01/22 00:29:27
 */


// jquery 扩展
$.fn.extend({
    "hideDropdown": function () {
        var self = $(this);
        if (self.hasClass("mobile")) {
            self.animate({
                "height": "0px"
            }).removeClass("active");
            self.parent().find(".dropdown-mask").hide();
            xnote.enableBodyScroll();
        } else {
            self.slideUp("fast");
        }
    }
});


xnote.disableBodyScroll = function (e) {
    // preventDefault 不能完全阻止滚动
    $("body").css("overflow", "hidden");
}

xnote.enableBodyScroll = function (e) {
    $("body").css("overflow", "auto");
}


xnote.toggleDropdown = function (target) {
    var dropdownContent = $(target).siblings(".dropdown-content");
    if (dropdownContent.hasClass("mobile")) {
        console.log("dropdown mobile");
        // 移动端动画
        if (dropdownContent.hasClass("active")) {
            // 展示 -> 隐藏
            dropdownContent.hideDropdown();
        } else {
            // 隐藏 -> 展示
            $(target).parent().find(".dropdown-mask").show();
            dropdownContent.show().animate({
                "height": "60%"
            }).addClass("active");
            xnote.disableBodyScroll();
        }
    } else {
        dropdownContent.slideToggle("fast");
        if (dropdownContent.offset() && dropdownContent.offset().left < 0) {
            dropdownContent.css("left", 0);
        }

        $(".dropdown-content").each(function (index, element) {
            if (element != dropdownContent[0]) {
                $(element).slideUp(0);
            }
        });
    }
}

$(function () {
    $(".dropdown").click(function (e) {
        xnote.toggleDropdown(e.target);
    });

    $(".x-dropdown").click(function (e) {
        xnote.toggleDropdown(e.target);
    });

    $("body").on("click", function (e) {
        var target = e.target;
        if ($(target).hasClass("dropdown") || $(target).hasClass("dropdown-btn")) {
            return;
        }
        $(".dropdown-content").hideDropdown();
    });

});

