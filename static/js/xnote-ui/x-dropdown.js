/** 下拉组件
 * @since 2020/01/11
 * @modified 2020/01/22 00:29:27
 */

$(function () {
    // Dropdown 控件

    function toggleDropdown(e) {
        var target = e.target;
        var dropdownContent = $(target).next(".dropdown-content");
        dropdownContent.slideToggle("fast");

        $(".dropdown-content").each(function (index, element) {
            if (element != dropdownContent[0]) {
                $(element).slideUp(0);
            }
        })
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
