//源文件: https://gitee.com/sentsin/layer/blob/master/src/layer.js
//layer相册层修改版, 调整了图片大小的处理
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

  // 状态
  dict.state = {};
  dict.state.rotate = 0; // 旋转角度
  dict.state.img = null; // 图片资源
  
  options.img = options.img || 'img';
  // 是否是移动设备
  options.isMobile = options.isMobile || false;
  
  var success = options.success;
  delete options.success;

  if(!type){ //页面直接获取
    var parent = $(options.photos);
    var pushData = function(){
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

  // 重绘图片
  dict.repaint = function(layero) {
    console.log("layero", layero);
    var img = dict.state.img;
    var imgarea = [img.width, img.height];
    var isRotate90 = dict.state.rotate == 90 || dict.state.rotate == 270;

    if (isRotate90) {
      imgarea = [img.height, img.width];
    } 
    
    console.log("imgarea", imgarea);
    var area = dict.calcArea(imgarea, options, true);
    console.log("area", area);

    var width = area[0];
    var height = area[1];
    var top = ($(window).height() - height) / 2;
    var left = ($(window).width() - width) / 2;

    var style = {
      "width": width + "px",
      "height": height + "px",
      "left": left + "px",
      "top": top + "px",
    };

    console.log("repaint style", style);

    var imgLeft = 0;
    var imgTop = 0;

    if (isRotate90) {
      // transform是在定位确认之后以元素中心旋转
      // 所以旋转90的定位还是按照旋转之前的位置计算
      imgLeft = ($(window).width()-height)/2;
      imgTop = ($(window).height()-width)/2;
    }

    var imgCss = {
      "position": "relative",
      "width": "100%",
      "left": 0,
      "top": 0
    };

    if (isRotate90) {
      imgCss = {
        "position": "fixed",
        "width": height,
        "left": imgLeft,
        "top": imgTop
      };
    }

    console.log("img css", imgCss);

    // 渲染样式
    layero.css(style);
    layero.find(".layui-layer-content").css("height", height);
    layero.find("img").css(imgCss);
  }

  // 计算图片大小
  dict.calcArea = function (imgarea, options, returnNumber) {
    var winarea;

    if (options.isMobile) {
      // 移动端不需要预留空间，直接填满屏幕即可
      // 64是上下控制栏各32px
      winarea = [$(window).width(), $(window).height()-64];
    } else {
      winarea = [$(window).width() - 100, $(window).height() - 100];
    }
    
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

    // 图片太小了，进行放大
    var minsize = 150;
    if (imgarea[0] < minsize && imgarea[1] < minsize) {
      var ratio = Math.min(minsize/imgarea[0], minsize/imgarea[1]);
      imgarea[0] = imgarea[0]*ratio;
      imgarea[1] = imgarea[1]*ratio;
    }

    if (returnNumber) {
      return imgarea;
    }
    
    return [imgarea[0]+'px', imgarea[1]+'px']; 
  }
  
  //一些动作
  dict.event = function(layero){
    
    // layer默认的行为
    // dict.bigimgPic.hover(function(){
    //   dict.imgsee.show();
    // }, function(){
    //   dict.imgsee.hide();
    // });

    dict.bigimgPic.click(function() {
      dict.imgsee.toggle();
    });

    // dict.imgsee.show();
    // $(".layui-layer-imgprev").css("position", "fixed");
    // $(".layui-layer-imgnext").css("position", "fixed");
    
    dict.bigimg.find('.layui-layer-imgprev').on('click', function(event){
      event.preventDefault();
      dict.imgprev();
    });  
    
    dict.bigimg.find('.layui-layer-imgnext').on('click', function(event){     
      event.preventDefault();
      dict.imgnext();
    });

    dict.bigimg.find(".close-span").on("click", function(event) {
      layer.close(dict.index);
    });

    dict.bigimg.find(".rotate-span").on("click", function(event) {
      dict.state.rotate += 90;
      dict.state.rotate %= 360;
      dict.bigimg.find("img").css("transform", "rotate(" + dict.state.rotate + "deg)");
      // 重新绘制弹窗
      dict.repaint(layero);
    })
    
    $(document).on('keyup', dict.keyup);

    // 触控事件
    var hammer = options.hammer;
    if (hammer) {
      hammer.on('swipeleft', function(e) {
        dict.imgprev();
      });
      hammer.on('swiperight', function(e) {
        dict.imgnext();
      });
    }
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

  function imgBarTop() {
    if (options.hideBar) {
      return "";
    }
    var bar = $("<div>").addClass("layui-layer-imgbar").addClass("imgbar-top").hide();

    // 旋转图片功能
    bar.append($("<span>").addClass("rotate-span").addClass("clickable").text("旋转"));
    bar.append("&nbsp;");

    var rightBox = $("<div>").addClass("float-right");
    rightBox.append($("<span>").addClass("close-span").addClass("clickable").text("关闭"));

    bar.append(rightBox);
    return bar.prop("outerHTML");
  }

  function imgBarBottom() {
    if (options.hideBar) {
      return "";
    }
    return '<div class="layui-layer-imgbar imgbar-bottom" style="display:'
      + (key ? 'block' : '') 
      + '"><span class="layui-layer-imgtit"><a target="_blank" href="' 
      + data[start].src +  '">'+ (data[start].alt||'') 
      + '</a><em>'+ dict.imgIndex +'/'+ data.length +'</em></span></div>';
  }

  loadImage(data[start].src, function(img){
    // 存储图像资源
    dict.state.img = img;

    layer.close(dict.loadi);
    dict.index = layer.open($.extend({
      type: 1,
      id: 'layui-layer-photos',
      area: dict.calcArea([img.width, img.height], options),
      title: false,
      shade: 0.9,
      shadeClose: true,
      closeBtn: false,
      // move: '.layui-layer-phimg img',
      move: false,
      moveType: 1,
      scrollbar: false,
      // 是否移出窗口
      moveOut: false,
      // anim: Math.random()*5|0,
      isOutAnim: false,
      skin: 'layui-layer-photos' + skin('photos'),
      content: '<div class="layui-layer-phimg">'
        +imgBarTop()
        +'<img src="'+ data[start].src +'" alt="'+ (data[start].alt||'') +'" layer-pid="'+ data[start].pid +'">'
        +'<div class="layui-layer-imgsee">'
          +(data.length > 1 ? '<span class="layui-layer-imguide"><a href="javascript:;" class="layui-layer-iconext layui-layer-imgprev"></a><a href="javascript:;" class="layui-layer-iconext layui-layer-imgnext"></a></span>' : '')
          +imgBarBottom()
        +'</div>'
      +'</div>',
      success: function(layero, index){
        dict.bigimg = layero.find('.layui-layer-phimg');
        dict.bigimgPic = layero.find('.layui-layer-phimg img');
        dict.imgsee = layero.find(".layui-layer-imgbar");

        // 左右方向图标始终展示
        layero.find(".layui-layer-imgnext,.layui-layer-imgprev").
          css("position", "fixed").show();
        layero.find(".layui-layer-imguide").show();
        layero.find(".layui-layer-imgbar").show();

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
