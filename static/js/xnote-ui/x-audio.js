/** audio.js, part of xnote-ui 
 * @since 2020/01/05
 * @modified 2022/01/09 16:09:02
 **/

$(function(e) {

    // 默认不启用
    var audioEnabled = false;

    $("body").on("click", ".x-audio", function(e) {
        var src = $(this).attr("data-src");
        layer.open({
            type: 2,
            content: src,
            shade: 0
        });
    });

    var AUDIO_MAP = {};

    xnote.loadAudio = function (id, src) {
        AUDIO_MAP[id] = new Audio(src);
    }

    xnote.playAudio = function (id) {
        if (!audioEnabled) {
            return;
        }

        var audioObject = AUDIO_MAP[id];
        if (audioObject) {
            audioObject.play();
        }
    }

});
