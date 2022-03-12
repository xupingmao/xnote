/** x-tab.js
 * tab页功能，依赖jQuery
 * 有两个样式: tab-link 和 tab-btn
 */

$(function (e) {

    function initTabBtn() {
        var hasActive = false;
        var count = 0;
        var pathAndSearch = location.pathname + location.search;

        $(".x-tab-btn").each(function(index, ele) {
            var link = $(ele).attr("href");
            if (pathAndSearch == link) {
                $(ele).addClass("active");
                hasActive = true;
            }

            count += 1;
        });

        if (count > 0 && !hasActive) {
            $(".x-tab-default").addClass("active");
        }
    }

    function initTabBox() {
        $(".x-tab-box").each(function (index, ele) {
            var key = $(ele).attr("data-tab-key");
            var defaultValue = $(ele).attr("data-tab-default");
            var tabStyle = $(ele).attr("data-tab-style");

            var value = getUrlParam(key);
            if ( xnote.isEmpty(value) ) {
                value = defaultValue;
            }

            // 样式通过CSS控制即可
            console.log("tab-value=",value);
            var qValue = '"' + value + '"'; // 加引号quote

            $(ele).find(".x-tab[data-tab-value=" + qValue + "]").addClass("active");
            $(ele).find(".x-tab-btn[data-tab-value=" + qValue + "]").addClass("active");

            $(ele).find(".x-tab").each(function (index, child) {
                var oldHref = $(child).attr("href");
                if ( xnote.isNotEmpty(oldHref) ) {
                    return;
                }
                var tabValue = $(child).attr("data-tab-value")
                $(child).attr("href", addUrlParam(window.location.href, key, tabValue))
            })
        });
    }


    function initTabDefault() {
        // initTabLink();
        initTabBtn();
        initTabBox();
    }

    initTabDefault();
    xnote.addEventListener("init-default-value", initTabDefault);
});
