(function (window) {

    if (self != top) {
        // in iframe
        return;
    }

    var width = 960;
    var maxWidth = $(window).width();
    var maxHeight = $(window).height();

    var btnRight = (maxWidth - width) / 2 + 20;
    if (btnRight < 0) {
        btnRight = 20;
    }
    var botHeight = maxHeight - 100;

    var bots = {};

    function createIframe(src) {
        return $("<iframe>").css({
            "float": "left",
            "width": "100%",
            "height": "100%",
            "border": "none"
        }).attr("src", src);
    }

    function getBottomBot() {
        if (bots.bottom) {
            return bots.bottom;
        }
        var bot = $("<div>").css({"position": "fixed", 
                "width": "100%", 
                "height": "200px",
                "background-color": "#ccc",
                "bottom": "0px",
                "right": "0px",
                "z-index": 50
            }).append(createIframe("/"));
        bot.hide();
        bot.attr("id", "x-bot");
        $(document.body).append(bot);
        bots.bottom = bot;
        return bot;
    }

    function getRightBot() {
        if (bots.right) {
            return bots.right;
        }
        var rightBot = $("<div>").css({
            "position": "fixed",
            "width": "360px",
            "right": "0px",
            "bottom": "0px",
            "height": botHeight,
            "background-color": "#fff",
            "border": "solid 1px #ccc",
            "z-index": 50
        }).append(createIframe("/message?status=all"));
        rightBot.hide();
        $(document.body).append(rightBot);
        bots.right = rightBot;
        return rightBot;
    }

    function init() {
        var botBtn = $("<div>").css({
            "position": "fixed",
            "bottom": "50px",
            "right": btnRight,
            "width": "50px",
            "height": "40px",
            "background-color": "#00c1de",
            "cursor": "pointer",
            "border-radius": "5px",
            "color": "#fff",
            "padding": "10px",
            "z-index": 100,
            "opacity": 0.8
        })
        .text("Help")
        .addClass("bot-btn");

        $(document.body).append(botBtn);
        $(".bot-btn").click(function () {
            // getBottomBot().slideToggle(200);
            // getRightBot().slideToggle(200);
            getRightBot().animate({"width": "toggle"}, 200);
        })
    }

    $(function () {
        init();
    });
})(window);