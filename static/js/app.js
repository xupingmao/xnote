/**
* 通用的操作函数
*/
$(function () {
  
  window.moveTo = function (selfId, parentId) {
    $.post("/note/move",
    { id: selfId, parent_id: parentId },
    function (resp) {
      console.log(resp);
      window.location.reload();
    });
  }
  
  function showSideBar() {
    $(".navMenubox").animate({ "margin-left": "0px" });
    $("#poweredBy").show();
  }
  
  function hideSideBar() {
    $(".navMenubox").animate({ "margin-left": "-200px" });
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
});

/**
* 处理悬浮控件
*/
$(function () {
  var width = 960;
  var maxWidth = $(window).width();
  var maxHeight = $(window).height();
  var leftPartWidth = 200;
  
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
    var bot = $("<div>").css({
      "position": "fixed",
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
    var mainWidth = $(".root").width();
    var bot = $("<div>").css({
      "position": "fixed",
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
    console.log("init");
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
    $("body").on("click", ".layer-btn", function (event) {
      console.log("click");
      var target = event.target;
      var url = $(target).attr("data-url");
      openDialog(url);
    });
    console.log("init done");
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
  
  function initSearchBoxWidth() {
    if (window.SHOW_ASIDE == "False") {
      $(".nav-left-search").css("width", "100%");
    }
  }
  
  function init() {
    // var botBtn = $("<div>").text("工具").css("right", btnRight).addClass("bot-btn");
    // $(document.body).append(botBtn);
    $(".bot-btn").click(function () {
      getRightBot().fadeToggle(200);
    });
    initSearchBoxWidth();
    initEventHandlers();
  }
  
  function showIframeDialog(src) {
    getRightBot().fadeIn(200);
    $("#botIframe").attr("src", src);
  }
  
  function hideIframeDialog() {
    getRightBot().fadeOut(200);
  }
  
  window.openDialog = function (url) {
    var width = $(".root").width() - 40;
    var area;
    
    if (isMobile()) {
      area = ['100%', '100%'];
    } else {
      area = [width + 'px', '80%'];
    }
    
    layer.open({
      type: 2,
      shadeClose: true,
      title: '子页面',
      maxmin: true,
      area: area,
      content: url,
      scrollbar: false
    });
  }
  
  window.showIframeDialog = showIframeDialog;
  window.hideIframeDialog = hideIframeDialog;
  
  window.toggleMenu = function () {
    $(".aside-background").toggle();
    $(".aside").toggle(500);
  }
  
  /**
  * 调整高度，通过
  * @param {string} selector 选择器
  * @param {number} bottom 距离窗口底部的距离
  */
  window.adjustHeight = function (selector, bottom, options) {
    bottom = bottom || 0;
    var height = getWindowHeight() - $(selector).offset().top - bottom;
    $(selector).css("height", height).css("overflow", "auto");
    
    if (options != undefined) {
      if (options.overflow) {
        $(selector).css("overflow", options.overflow);
      }
    }
    
    return height;
  }
  
  /**
  * 调整导航栏，如果在iframe中，则不显示菜单
  */
  window.adjustNav = function () {
    if (self != top) {
      $(".nav").hide();
      $(".root").css("padding", "10px");
    }
  }
  
  window.adjustTable = function () {
    $("table").each(function (index, element) {
      var count = $(element).find("th").length;
      if (count > 0) {
        $(element).find("th").css("width", 100 / count + '%');
      }
    });
  }
  
  $(".aside-background").on('click', function () {
    toggleMenu();
  });
  
  
  if (window.PAGE_OPEN == "dialog") {
    // 使用对话框浏览笔记
    $(".dialog-link").click(function (e) {
      e.preventDefault();
      var url = $(this).attr("href");
      var width = $(".root").width();
      layer.open({
        type: 2,
        title: "查看",
        shadeClose: true,
        shade: 0.8,
        area: [width + "px", "90%"],
        scrollbar: false,
        content: url
      });
    });
  }
  
  function processInIframe() {
    
  }
  
  if (self != top) {
    processInIframe();
  }
  
  init();
});


xnote.events.fireUploadEvent = function (event) {
  xnote.fire("fs.upload", event);
};

xnote.events.onUploadEvent = function (listener) {
  xnote.on("fs.upload", listener);
};


xnote.events.fireUploadPrepareEvent = function (event) {
  console.log("fireUploadPrepareEvent", event);
  xnote.fire("fs.upload.prepare", event);
};

xnote.events.onUploadPrepareEvent = function (listener) {
  xnote.on("fs.upload.prepare", listener);
};
