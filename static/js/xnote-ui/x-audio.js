/** audio.js, part of xnote-ui 
 * @since 2020/01/05
 * @modified 2020/01/05 23:53:02
 **/


$(function (e) {

  $("body").on("click", ".x-audio", function (e) {
    var src = $(this).attr("data-src");
    layer.open({
      type: 2,
      content: src,
      shade: 0
    });
  });
  
})