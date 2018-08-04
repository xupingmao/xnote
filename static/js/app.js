/**
 * 通用的操作函数
 */
$(function() {

  function moveTo(selfId, parentId) {
      $.post("/file/group/move", 
          {id:selfId, parent_id: parentId}, 
          function (resp){
              console.log(resp);
              window.location.reload();
      });
  }
  window.moveTo = moveTo;

  function showSideBar() {
    $(".navMenubox").animate({"margin-left": "0px"});
    $("#poweredBy").show();
  }

  function hideSideBar() {
    $(".navMenubox").animate({"margin-left": "-200px"});
    $("#poweredBy").hide();
  }

  function checkResize() {
    if ($(".navMenubox").is(":animated")) {
      return;
    }
    if (window.innerWidth < 600) {
      // 移动端，兼容下不支持@media的浏览器 
      hideSideBar();
    } else {
      showSideBar();
    }
  }

  function toggleMenu() {
    var marginLeft = $(".navMenubox").css("margin-left");
    if (marginLeft == "0px") {
      hideSideBar();
    } else {
      showSideBar();
    }
  }

  $(".toggleMenu").on("click", function () {
    toggleMenu();
  });

  $(".move-btn").click(function (event) {
      var url = $(event.target).attr("data-url");
      $.get(url, function (respHtml) {
          var width = $(".main").width();
          layer.open({
            type: 1,
            title: "移动分组",
            shadeClose: true,
            area: [width + "px", '80%'],
            content: respHtml,
            scrollbar: false
          });
      });
  });
});

/**
 * 处理悬浮控件
 */
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
    var botHeight = "100%";
    var botWidth = maxWidth / 2;

    var bots = {};

    function createIframe(src) {
        return $("<iframe>")
          .addClass("dialog-iframe")
          .attr("src", src)
          .attr("id", "botIframe");
    }

    function createCloseBtn() {
      return $("<span>").text("Close").addClass("dialog-close-btn");
    }

    function createTitle() {
      var btn1 = $("<span>").text("Home").addClass("dialog-title-btn dialog-home-btn");
      var btn2 = $("<span>").text("Tools").addClass("dialog-title-btn dialog-tools-btn");
      var btn3 = $("<span>").text("Refresh").addClass("dialog-title-btn dialog-refresh-btn");

      return $("<div>").addClass("dialog-title")
        .append(createCloseBtn())
        .append(btn1).append(btn2).append(btn3);
    }

    function getBottomBot() {
        if (bots.bottom) {
            return bots.bottom;
        }
        var bot = $("<div>").css({"position": "fixed", 
                "width": "100%", 
                "height": "80%",
                "background-color": "#fff",
                "border": "1px solid #ccc",
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

    function getIframeDialog() {
      if (bots.dialog) {
        return bots.dialog;
      }
      var mainWidth = $(".main").width();
      var bot = $("<div>").css({"position": "fixed", 
                "width": mainWidth, 
                "height": "80%",
                "background-color": "#fff",
                "border": "1px solid #ccc",
                "bottom": "0px",
                "right": "0px",
                "z-index": 50
            }).append(createIframe("/"));
        bot.hide();
        $(document.body).append(bot);
        bots.dialog = bot;
        return bot;
    }

    function initEventHandlers() {
      // close button event
      $("body").on("click", ".dialog-close-btn", function () {
        getRightBot().fadeOut(200);
      });
      $("body").on("click", ".dialog-home-btn", function () {
        $(".right-bot iframe").attr("src", "/");
      });
      $("body").on("click", ".dialog-tools-btn", function () {
        $(".right-bot iframe").attr("src", "/fs_api/plugins");
      });
      $("body").on("click", ".dialog-refresh-btn", function () {
        $(".right-bot iframe")[0].contentWindow.location.reload();
      });

      $(".layer-btn").click(function (event) {
        var target = event.target;
        var url = $(target).attr("data-url");
        openDialog(url);
      })
    }

    function getRightBot() {
        if (bots.right) {
            return bots.right;
        }
        var width = "50%";
        if (maxWidth < 600) {
          width = "100%";
        }
        var rightBot = $("<div>").css({
            "position": "fixed",
            "width": width,
            "right": "0px",
            "bottom": "0px",
            "top": "0px",
            "background-color": "#fff",
            "border": "solid 1px #ccc",
            "z-index": 50,
        }).append(createTitle())
          .append(createIframe("/system/index"))
          .addClass("right-bot");
        rightBot.hide();
        $(document.body).append(rightBot);
        bots.right = rightBot;
        return rightBot;
    }

    function init() {
        // var botBtn = $("<div>").text("工具").css("right", btnRight).addClass("bot-btn");
        // $(document.body).append(botBtn);
        $(".bot-btn").click(function () {
            getRightBot().fadeToggle(200);
        });
        initEventHandlers();
    }

    function showIframeDialog(src) {
      getRightBot().fadeIn(200);
      $("#botIframe").attr("src", src);
    }

    function hideIframeDialog() {
      getRightBot().fadeOut(200);
    }

    function openDialog(url) {
      var width = $(".main").width();
      layer.open({
        type: 2,
        title: '子页面',
        maxmin: true,
        area: [width + "px", '80%'],
        content: url,
        scrollbar: false
      });
    }

    function openFileOption(e) {
      console.log(e);
      var path = $(e).attr("data-path");
      openDialog("/fs_api/plugins?path=" + path);
    }

    window.openDialog = openDialog;
    window.openFileOption = openFileOption;
    window.showIframeDialog = showIframeDialog;
    window.hideIframeDialog = hideIframeDialog;

    $(function () {
        init();
    });
})(window);
