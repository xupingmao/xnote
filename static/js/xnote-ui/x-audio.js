/** audio.js, part of xnote-ui 
 * @since 2020/01/05
 * @modified 2021/05/03 12:58:59
 **/

$(function(e) {

    if (window.xnote === undefined) {
        window.xnote = {}
    }

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
        var audioObject = AUDIO_MAP[id];
        if (audioObject) {
            audioObject.play();
        }
    }

})