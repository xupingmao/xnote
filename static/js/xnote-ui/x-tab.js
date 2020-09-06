/** x-tab.js
 * tab页功能，依赖jQuery
 * 有两个样式: tab-link 和 tab-btn
 */

$(function (e) {

    // 类似tab的超链接
    function initTabLink() {
        var hasActive = false;
        var count = 0;
        $(".x-tab").each(function(index, ele) {
            var link = $(ele).attr("href");
            var fullpath = location.href;

            if (fullpath.indexOf(link) >= 0) {
                $(ele).addClass("tab-link-active");
                hasActive = true;
            }
            count += 1;
        });
        if (count > 0 && !hasActive) {
            $(".x-tab-default").addClass("tab-link-active");
        }
    }

    function initTabBtn() {
        var hasActive = false;
        var count = 0;
        $(".x-tab-btn").each(function(index, ele) {
            var link = $(ele).attr("href");
            var fullpath = location.href;

            if (fullpath.indexOf(link) >= 0) {
                $(ele).addClass("x-tab-btn-active");
                hasActive = true;
            }

            count += 1;
        });

        if (count > 0 && !hasActive) {
            $(".x-tab-default").addClass("x-tab-btn-active");
        }
    }

    initTabLink();
    initTabBtn();
});
