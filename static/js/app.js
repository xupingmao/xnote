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
      })
      $("body").on("click", ".dialog-refresh-btn", function () {
        $(".right-bot iframe")[0].contentWindow.location.reload();
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
        var botBtn = $("<div>").text("工具").css("right", btnRight).addClass("bot-btn");
        $(document.body).append(botBtn);
        $(".bot-btn").click(function () {
            getRightBot().fadeToggle(200);
        });

        $(window).on("error", function (message, source, lineno, colno, error) {
            showToast(message);
        })

        initEventHandlers();
    }

    function showIframeDialog(src) {
      getRightBot().fadeIn(200);
      $("#botIframe").attr("src", src);
    }

    function hideIframeDialog() {
      getRightBot().fadeOut(200);
    }

    window.showIframeDialog = showIframeDialog;
    window.hideIframeDialog = hideIframeDialog;

    $(function () {
        init();

        // window.onbeforeunload = function(e) {
        //   var dialogText = 'Dialog text here';
        //   e.returnValue = dialogText;
        //   return dialogText;
        // };
        // function onunloadHandler(){
        //     var warning="谢谢光临";
        //     alert(warning);
        // }
        // window.onbeforeunload = onbeforeunloadHandler;
        // window.onunload = onunloadHandler;
    });
})(window);


$(function() {
  function expandMenu(ele, delay) {
    // 禁用
    return;
    if (delay == undefined) {
      delay = 0;
    }
    var parent = ele.parent().parent(); //获取当前页签的父级的父级
    var labeul = ele.parent("li").find(">ul");
    if (ele.parent().hasClass('open') == false) {
      //展开未展开
      parent.find('ul').slideUp(delay);
      parent.find("li").removeClass("open");
      parent.find('li a').removeClass("active").find(".arrow").removeClass("open");
      ele.parent("li").addClass("open").find(labeul).slideDown(delay);
      ele.addClass("active").find(".arrow").addClass("open")
    } else {
      ele.parent("li").removeClass("open").find(labeul).slideUp(delay);
      if (ele.parent().find("ul").length > 0) {
        ele.removeClass("active").find(".arrow").removeClass("open");
      } else {
        ele.addClass("active");
      }
    }
  }
  // nav收缩展开
  $('.navMenu li a').on('click',
    function() {
      expandMenu($(this), 300);
  });


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

  var pathname = location.pathname;
  if (/\/file\/.*/.test(pathname)) {
    expandMenu($("#navFile"));
  }
  if (pathname != "/tools/message"
      && (/\/system\/.*/.test(pathname) 
      || /\/tools\/.*/.test(pathname))) {
    expandMenu($("#navSystem"));
  }
});
