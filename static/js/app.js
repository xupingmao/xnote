/**
 * 通用的操作函数
 */
$(function() {

  // 设置最小的高度
  $(".main").css("min-height", getWindowHeight());

  window.moveTo = function (selfId, parentId) {
      $.post("/note/group/move", 
          {id:selfId, parent_id: parentId}, 
          function (resp){
              console.log(resp);
              window.location.reload();
      });
  }

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
$(function () {
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

    window.openDialog = function (url) {
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

    window.openFileOption = function (e) {
      console.log(e);
      var path = $(e).attr("data-path");
      openDialog("/fs_api/plugins?path=" + path);
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
    window.adjustHeight = function (selector, bottom) {
      bottom = bottom || 0;
      var height = getWindowHeight() - $(selector).offset().top - bottom;
      $(selector).css("height", height);
      return height;
    }

    /**
     * 调整导航栏，如果在iframe中，则不显示菜单
     */
    window.adjustNav = function () {
      if (self != top) {
        $(".nav").hide();
        $(".main").css("padding", "10px");
      }
    }

    $(".aside-background").on('click', function () {
      toggleMenu();
    });


    if (window.PAGE_OPEN == "dialog") {    
      // 使用对话框浏览笔记
      $(".dialog-link").click(function (e) {
          e.preventDefault();
          var url = $(this).attr("href");
          var width = $(".main").width();
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

    // if (self == top) {
      // 不是处于iframe环境
    // }
    init();
});

/**
 * xnote的公有方法
 */
var BASE_URL = "/static/lib/webuploader";

// xnote全局对象
var xnote = {
  createUploader: function () {
    return WebUploader.create({
            // 选完文件后，是否自动上传。
            auto: true,
            // swf文件路径
            swf: BASE_URL + '/Uploader.swf',
            // 文件接收服务端。
            server: '/fs_upload/range',
            // 选择文件的按钮。可选。
            // 内部根据当前运行是创建，可能是input元素，也可能是flash.
            pick: '#filePicker',
            // 需要分片
            chunked: true,
            // 默认5M
            // chunkSize: 1024 * 1024 * 5,
            chunkSize: 1024 * 1024 * 5,
            // 重试次数
            chunkRetry: 10,
            // 文件上传域的name
            fileVal: "file",
            // 不开启并发
            threads: 1
            // 默认压缩是开启的
            // compress: {}
        });
  },

  // 把blob对象转换成文件上传到服务器
  uploadBlob: function (blob, prefix, successFn, errorFn) {
    var fd = new FormData();
    fd.append("file", blob);
    fd.append("prefix", prefix);
    fd.append("name", "auto");
    //创建XMLHttpRequest对象
    var xhr = new XMLHttpRequest();
    xhr.open('POST','/fs_upload');
    xhr.onload = function () {
        if ( xhr.readyState === 4 ) {
            if ( xhr.status === 200 ) {
                var data = JSON.parse( xhr.responseText );
                if (successFn) {
                  successFn(data);
                } else {
                  console.log(data);
                }
            } else {
                console.error( xhr.statusText );
            }
        };
    };
    xhr.onerror = function (e) {
        console.log( xhr.statusText );
    }
    xhr.send(fd);
  }
}

//layer相册层修改版
layer.photos = function(options, loop, key){
  var cache = layer.cache||{}, skin = function(type){
    return (cache.skin ? (' ' + cache.skin + ' ' + cache.skin + '-'+type) : '');
  }; 
 
  var dict = {};
  options = options || {};
  if(!options.photos) return;
  var type = options.photos.constructor === Object;
  var photos = type ? options.photos : {}, data = photos.data || [];
  var start = photos.start || 0;
  dict.imgIndex = (start|0) + 1;
  
  options.img = options.img || 'img';
  
  var success = options.success;
  delete options.success;

  if(!type){ //页面直接获取
    var parent = $(options.photos), pushData = function(){
      data = [];
      parent.find(options.img).each(function(index){
        var othis = $(this);
        othis.attr('layer-index', index);
        data.push({
          alt: othis.attr('alt'),
          pid: othis.attr('layer-pid'),
          src: othis.attr('layer-src') || othis.attr('src'),
          thumb: othis.attr('src')
        });
      })
    };
    
    pushData();
    
    if (data.length === 0) return;
    
    loop || parent.on('click', options.img, function(){
      var othis = $(this), index = othis.attr('layer-index'); 
      layer.photos($.extend(options, {
        photos: {
          start: index,
          data: data,
          tab: options.tab
        },
        full: options.full
      }), true);
      pushData();
    })
    
    //不直接弹出
    if(!loop) return;
    
  } else if (data.length === 0){
    return layer.msg('&#x6CA1;&#x6709;&#x56FE;&#x7247;');
  }
  
  //上一张
  dict.imgprev = function(key){
    dict.imgIndex--;
    if(dict.imgIndex < 1){
      dict.imgIndex = data.length;
    }
    dict.tabimg(key);
  };
  
  //下一张
  dict.imgnext = function(key,errorMsg){
    dict.imgIndex++;
    if(dict.imgIndex > data.length){
      dict.imgIndex = 1;
      if (errorMsg) {return};
    }
    dict.tabimg(key)
  };
  
  //方向键
  dict.keyup = function(event){
    if(!dict.end){
      var code = event.keyCode;
      event.preventDefault();
      if(code === 37){
        dict.imgprev(true);
      } else if(code === 39) {
        dict.imgnext(true);
      } else if(code === 27) {
        layer.close(dict.index);
      }
    }
  }
  
  //切换
  dict.tabimg = function(key){
    if(data.length <= 1) return;
    photos.start = dict.imgIndex - 1;
    layer.close(dict.index);
    return layer.photos(options, true, key);
    setTimeout(function(){
      layer.photos(options, true, key);
    }, 200);
  }
  
  //一些动作
  dict.event = function(){
    // dict.bigimg.hover(function(){
    //   dict.imgsee.show();
    // }, function(){
    //   dict.imgsee.hide();
    // });
    dict.imgsee.show();
    $(".layui-layer-imgprev").css("position", "fixed");
    $(".layui-layer-imgnext").css("position", "fixed");
    
    dict.bigimg.find('.layui-layer-imgprev').on('click', function(event){
      event.preventDefault();
      dict.imgprev();
    });  
    
    dict.bigimg.find('.layui-layer-imgnext').on('click', function(event){     
      event.preventDefault();
      dict.imgnext();
    });
    
    $(document).on('keyup', dict.keyup);
  };
  
  //图片预加载
  function loadImage(url, callback, error) {   
    var img = new Image();
    img.src = url; 
    if(img.complete){
      return callback(img);
    }
    img.onload = function(){
      img.onload = null;
      callback(img);
    };
    img.onerror = function(e){
      img.onerror = null;
      error(e);
    };  
  };
  
  dict.loadi = layer.load(1, {
    shade: 'shade' in options ? false : 0.9,
    scrollbar: false
  });

  loadImage(data[start].src, function(img){
    layer.close(dict.loadi);
    dict.index = layer.open($.extend({
      type: 1,
      id: 'layui-layer-photos',
      area: function(){
        var imgarea = [img.width, img.height];
        var winarea = [$(window).width() - 100, $(window).height() - 100];
        
        //如果 实际图片的宽或者高比 屏幕大（那么进行缩放）
        if(!options.full && (imgarea[0]>winarea[0]||imgarea[1]>winarea[1])){
          var wh = [imgarea[0]/winarea[0],imgarea[1]/winarea[1]];//取宽度缩放比例、高度缩放比例
          if(wh[0] > wh[1]){//取缩放比例最大的进行缩放
            imgarea[0] = imgarea[0]/wh[0];
            imgarea[1] = imgarea[1]/wh[0];
          } else if(wh[0] < wh[1]){
            imgarea[0] = imgarea[0]/wh[1];
            imgarea[1] = imgarea[1]/wh[1];
          }
        }
        
        return [imgarea[0]+'px', imgarea[1]+'px']; 
      }(),
      title: false,
      shade: 0.9,
      shadeClose: true,
      closeBtn: false,
      move: '.layui-layer-phimg img',
      moveType: 1,
      scrollbar: false,
      moveOut: true,
      //anim: Math.random()*5|0,
      isOutAnim: false,
      skin: 'layui-layer-photos' + skin('photos'),
      content: '<div class="layui-layer-phimg">'
        +'<img src="'+ data[start].src +'" alt="'+ (data[start].alt||'') +'" layer-pid="'+ data[start].pid +'">'
        +'<div class="layui-layer-imgsee">'
          +(data.length > 1 ? '<span class="layui-layer-imguide"><a href="javascript:;" class="layui-layer-iconext layui-layer-imgprev"></a><a href="javascript:;" class="layui-layer-iconext layui-layer-imgnext"></a></span>' : '')
          +'<div class="layui-layer-imgbar" style="display:'+ (key ? 'block' : '') +'"><span class="layui-layer-imgtit"><a href="javascript:;">'+ (data[start].alt||'') +'</a><em>'+ dict.imgIndex +'/'+ data.length +'</em></span></div>'
        +'</div>'
      +'</div>',
      success: function(layero, index){
        dict.bigimg = layero.find('.layui-layer-phimg');
        dict.imgsee = layero.find('.layui-layer-imguide,.layui-layer-imgbar');
        dict.event(layero);
        options.tab && options.tab(data[start], layero);
        typeof success === 'function' && success(layero);
      }, end: function(){
        dict.end = true;
        $(document).off('keyup', dict.keyup);
      }
    }, options));
  }, function(){
    layer.close(dict.loadi);
    layer.msg('&#x5F53;&#x524D;&#x56FE;&#x7247;&#x5730;&#x5740;&#x5F02;&#x5E38;<br>&#x662F;&#x5426;&#x7EE7;&#x7EED;&#x67E5;&#x770B;&#x4E0B;&#x4E00;&#x5F20;&#xFF1F;', {
      time: 30000, 
      btn: ['&#x4E0B;&#x4E00;&#x5F20;', '&#x4E0D;&#x770B;&#x4E86;'], 
      yes: function(){
        data.length > 1 && dict.imgnext(true,true);
      }
    });
  });
};

