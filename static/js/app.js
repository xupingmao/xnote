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
            "width": botWidth,
            "right": "0px",
            "bottom": "0px",
            "height": botHeight,
            "background-color": "#fff",
            "border-left": "solid 2px #ccc",
            "z-index": 50
        }).append(createIframe("/system/index"));
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
            "font-size": "14px",
            "background-color": "#00c1de",
            "cursor": "pointer",
            "border-radius": "5px",
            "color": "#fff",
            "padding": "10px",
            "z-index": 100,
            "opacity": 0.8
        })
        .text("工具")
        .addClass("bot-btn");

        $(document.body).append(botBtn);
        $(".bot-btn").click(function () {
            // getBottomBot().slideToggle(200);
            // getRightBot().slideToggle(200);
            // $("#mainContent").toggleClass("col-md-6");
            getRightBot().animate({"width": "toggle"}, 200);
            
            /**
            var oldLocation = window.location.href;
            if (oldLocation.indexOf("command_center") >= 0) {
                window.location.href = "/";
            } else {
                window.location.href = "/tools/command_center";
            }
            */
        });

        $(window).on("error", function (message, source, lineno, colno, error) {
            showToast(message);
        })
    }

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
