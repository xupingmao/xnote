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

            var autoHref = $(ele).attr("data-auto-href");
            console.debug("----- autoHref:", autoHref);
            if (autoHref === "true") {
                $(ele).find(".x-tab").each(function (index, child) {
                    console.debug("----- autoHref:", child)
                    var tabValue = $(child).attr("data-tab-value")
                    $(child).attr("href", addUrlParam(window.location.href, key, tabValue))
                })
            }
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
