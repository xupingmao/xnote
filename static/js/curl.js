 $(document).ready(function (){
    var url = window.curl_url;

    function url_root(url) {
        var reg = /(https?:\/\/)(.*?)[\/$]/gi;
        var result = reg.exec(url);
        var head = result[1];
        var home = result[2];
        return head + home;
    }

    try {

        $.get("/curl?url="+url, function (result) {
             // $("#result").text(result);
             console.log("data received");
             var reg = /<a.*?href="(.*?)".*?>(.*?)<\/a>/gi;
             var link;
             var link_map = {};
             while (link = reg.exec(result)) {
                // console.log(link);
                var href = link[1];
                var text = link[2];
                var a_tag = $("<a>");
                a_tag.text(text);
                a_tag.attr("href", href);
                if (href.startsWith("#")) {
                    continue;
                }
                if (text == "#") {
                    // maybe hash link;
                    continue;
                }
                if (text.startsWith("<img")) {
                    // image pass
                    continue;
                }
                if (link_map[href]) {
                    continue;
                }
                link_map[href] = true;
                $("#link_list").append(a_tag);
                $("#link_list").append("<br>");
             }

             var img_reg = /<img.*?src="(.*?)".*?>/gi;

             var img;
             var img_map = {};

             while (img = img_reg.exec(result)) {
                var src = img[1];
                if (!src.startsWith("http")) {
                    var old_src = src;
                    var new_src = url_root(url) + old_src;
                    console.log(old_src, new_src);
                    src = new_src;
                } 

                if (img_map[src]) {
                    continue;
                }
                img_map[src] = true;
                $("#img_list").append($("<img>").attr("src", src));
                $("#img_list").append("<br>");
             }
        })
    } catch (e) {
        console.log("data received error", e);
        throw e;
    }

    function switchBtn(btn_id, div_id, show_text, hide_text) {
        $(btn_id).click(function () {
            if ($(div_id).hasClass("hide")) {
                $(div_id).removeClass("hide");
                $(div_id).show();
                $(btn_id).html(hide_text);
            } else {
                $(div_id).hide();
                $(div_id).addClass("hide");
                $(btn_id).html(show_text);
            }
        });
    }
    switchBtn("#link_list_hide", "#link_list", "Show-Links", "Hide-Links");
    switchBtn("#img_list_hide", "#img_list", "Show-Images", "Hide-Images");
});

    