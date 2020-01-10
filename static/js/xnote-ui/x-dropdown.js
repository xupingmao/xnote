/** 下拉组件
 * @since 2020/01/11
 * @modified 2020/01/11 00:48:25
 */

$(function () {
    // Dropdown 控件

    function toggleDropdown(e) {
        var target = e.target;
        $(target).next(".dropdown-content").slideToggle("fast");
    }

    $(".dropdown").click(function (e) {
        toggleDropdown(e);
    });

    $(".x-dropdown").click(function (e) {
        toggleDropdown(e);
    });

    $("body").on("click", function (e) {
        var target = e.target;
        if ($(target).hasClass("dropdown") || $(target).hasClass("dropdown-btn")) {
            return;
        }
        $(".dropdown-content").hide();
    });
});
