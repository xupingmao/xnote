/** audio.js, part of xnote-ui 
 * @since 2020/01/05
 * @modified 2020/01/21 20:13:34
 **/

$(function(e) {

    $("body").on("click", ".x-audio",
    function(e) {
        var src = $(this).attr("data-src");
        layer.open({
            type: 2,
            content: src,
            shade: 0
        });
    });

})