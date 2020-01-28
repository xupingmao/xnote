/** photo.js, part of xnote-ui **/

$(function () {
  // 图片处理
  $("body").on('click', ".x-photo", function (e) {
        // console.log(e);
        var src = $(this).attr("src");
        var alt = $(this).attr("alt");
        console.log(src);

        var data = [];
        var imageIndex = 0;
        var target = e.target;

        $(".x-photo").each(function(index, el) {
          if (el == target) {
            imageIndex = index;
          }

          var src = $(el).attr("data-src");
          if (!src) {
            src = $(el).attr("src");
          }
          
          data.push({
            "alt": $(el).attr("alt"),
            "pid": 0,
            "src": src,
            "thumb": ""
          });
        });

        layer.photos({
            "photos": {
                  "title": "", //相册标题
                  "id": 123, //相册id
                  "start": imageIndex, //初始显示的图片序号，默认0
                  "data": data
                },
            "anim":5
        });
  });
});
