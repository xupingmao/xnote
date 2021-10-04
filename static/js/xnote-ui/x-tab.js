/** x-tab.js
 * tab页功能，依赖jQuery
 * 有两个样式: tab-link 和 tab-btn
 */

$(function (e) {
    // 类似tab的超链接
    // function initTabLink() {
    //     var hasActive = false;
    //     var count = 0;
    //     $(".x-tab").each(function(index, ele) {
    //         var link = $(ele).attr("href");
    //         var fullpath = location.href;

    //         if (fullpath.indexOf(link) >= 0) {
    //             $(ele).addClass("tab-link-active");
    //             hasActive = true;
    //         }
    //         count += 1;
    //     });
    //     if (count > 0 && !hasActive) {
    //         $(".x-tab-default").addClass("tab-link-active");
    //     }
    // }

    function initTabBtn() {
        var hasActive = false;
        var count = 0;
        var pathAndSearch = location.pathname + location.search;

        $(".x-tab-btn").each(function(index, ele) {
            var link = $(ele).attr("href");
            if (pathAndSearch == link) {
                $(ele).addClass("x-tab-btn-active");
                hasActive = true;
            }

            count += 1;
        });

        if (count > 0 && !hasActive) {
            $(".x-tab-default").addClass("x-tab-btn-active");
        }
    }

    function initTabBox() {
        $(".x-tab-box").each(function (index, ele) {
            var key = $(ele).attr("data-tab-key");
            var defaultValue = $(ele).attr("data-tab-default");
            var value = getUrlParam(key);
            if (value == "" || value == undefined) {
                value = defaultValue;
            }
            console.log("tab-value=",value);
            $(ele).find(".x-tab[data-tab-value=" + value + "]").addClass("x-tab-link-active");
            $(ele).find(".x-tab-btn[data-tab-value=" + value + "]").addClass("x-tab-btn-active");
        });
    }

    // initTabLink();
    initTabBtn();
    initTabBox();
});
