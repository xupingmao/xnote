
// @author xupingmao
// @since 2017/08/16
// @modified 2020/01/24 14:32:05

/**
 * 获取请求参数
 */
var getUrlParams = function() {
    var params = {};
    var url = window.location.href;
    url = url.split("#")[0];
    var idx = url.indexOf("?");
    if(idx > 0) {
        var queryStr = url.substring(idx + 1);
        var args = queryStr.split("&");
        for(var i = 0, a, nv; a = args[i]; i++) {
            nv = args[i] = a.split("=");
            if (nv.length > 1) {
                var value = nv[1];
                try {
                    params[nv[0]] = decodeURIComponent(value);
                } catch (e) {
                    params[nv[0]] = value;
                    console.warn('decode error', e)
                }
            }
        }
    }
    return params;
};

/**
 * 根据key获取url参数值 
 * @param {string} key
 */
var getUrlParam = function (key) {
    return getUrlParams()[key];
}

/** 
* 获取窗口的宽度
*/
function getWindowWidth() {
    if (window.innerWidth) {
        return window.innerWidth;
    } else {
        // For IE
        return Math.min(document.body.clientHeight, document.documentElement.clientHeight);
    }
};

function getWindowHeight() {
    if (window.innerHeight) {
        return window.innerHeight;
    } else {
        // For IE
        return Math.min(document.body.clientWidth, document.documentElement.clientWidth);
    }
};

// 遍历对象
function objForEach(obj, fn) {
    var key = void 0,
        result = void 0;
    for (key in obj) {
        if (obj.hasOwnProperty(key)) {
            result = fn.call(obj, key, obj[key]);
            if (result === false) {
                break;
            }
        }
    }
};

// 遍历类数组
function arrForEach(fakeArr, fn) {
    var i = void 0,
        item = void 0,
        result = void 0;
    var length = fakeArr.length || 0;
    for (i = 0; i < length; i++) {
        item = fakeArr[i];
        result = fn.call(fakeArr, item, i);
        if (result === false) {
            break;
        }
    }
};


//////////////////////////////////////////////////////
// String 增强
//////////////////////////////////////////////////////
// 以下是ES5的String对象，from w3c.org
// 5.1 作为函数调用 String 构造器
// 5.1.1 String ( [ value ] )
// 5.2 String 构造器
// 5.2.1 new String ( [ value ] )
// 5.3 String 构造器的属性
// 5.3.1 String.prototype
// 5.3.2 String.fromCharCode ( [ char0 [ , char1 [ , … ] ] ] )
// 5.4 字符串原型对象的属性
// 5.4.1 String.prototype.constructor
// 5.4.2 String.prototype.toString ( )
// 5.4.3 String.prototype.valueOf ( )
// 5.4.4 String.prototype.charAt (pos)
// 5.4.5 String.prototype.charCodeAt (pos)
// 5.4.6 String.prototype.concat ( [ string1 [ , string2 [ , … ] ] ] )
// 5.4.7 String.prototype.indexOf (searchString, position)
// 5.4.8 String.prototype.lastIndexOf (searchString, position)
// 5.4.9 String.prototype.localeCompare (that)
// 5.4.10 String.prototype.match (regexp)
// 5.4.11 String.prototype.replace (searchValue, replaceValue)
// 5.4.12 String.prototype.search (regexp)
// 5.4.13 String.prototype.slice (start, end)
// 5.4.14 String.prototype.split (separator, limit)
// 5.4.15 String.prototype.substring (start, end)
// 5.4.16 String.prototype.toLowerCase ( )
// 5.4.17 String.prototype.toLocaleLowerCase ( )
// 5.4.18 String.prototype.toUpperCase ( )
// 5.4.19 String.prototype.toLocaleUpperCase ( )
// 5.4.20 String.prototype.trim ( )
// 5.5 String 实例的属性
// 5.5.1 length
// 5.5.2 [[GetOwnProperty]] ( P )

var HEXMAP = {
        "0":0, '1':1, '2':2, '3':3,
        '4':4, '5':5, '6':6, '7':7,
        '8':8, '9':9, '0':0,
        'a':10, 'b':11, 'c':12, 'd':13,
        'e':14, 'f':15,
        'A':10, 'B':11, 'C':12, 'D':13,
        'E':14, 'F':15
    };

var BINMAP = {
        "0":0, '1':1, '2':2, '3':3,
        '4':4, '5':5, '6':6, '7':7,
        '8':8, '9':9, '0':0
    };

function _strfill(len, c) {
    c = c || ' ';
    s = "";
    for(var i = 0; i < len; i++) {
        s += c;
    }
    return s;
}

function _fmtnum(numval, length) {
    var max = Math.pow(10, length);
    if (numval > max) {
        return "" + numval;
    } else {
        var cnt = 1;
        var num = numval;
        num /= 10;
        while (num >= 1) {
            cnt+=1;
            num /= 10;
        }
        // what if the num is negative?
        var zeros = length - cnt;
        return _strfill(zeros, '0') + numval;
    }
}



function _fmtstr(strval, limit) {
    if (strval.length < limit) {
        return strval + _strfill(limit - strval.length);
    } else {
        strval = strval.substr(0, limit);
        return strval;
    }
}

function sFormat(fmt) {
    var dest = "";
    var idx = 1;
    var hexmap = BINMAP;
    for(var i = 0; i < fmt.length; i++) {
        var c = fmt[i];
        if (c == '%') {
            switch (fmt[i+1]) {
                case 's':
                case 'd':
                    i+=1;
                    dest += arguments[idx];
                    idx+=1;
                    break;
                case '%':
                    i+=1;
                    dest += '%';
                    break;
                case '0':
                case '1':
                case '2':
                case '3': case '4': case '5':
                case '6': case '7': case '8':
                case '8': case '9': {
                    var length = 0;
                    i += 1;
                    while (hexmap[fmt[i]] != undefined) {
                        length = length * 10 + hexmap[fmt[i]];
                        i+=1;
                    }
                    if (fmt[i] == 'd') {
                        var val = 0;
                        try {
                            val = parseInt(arguments[idx]);
                        } catch (e) {
                            console.log(e);
                            dest += 'NaN';
                            idx+=1;
                            break;
                        }
                        idx+=1;
                        dest += _fmtnum(val, length);
                    } else if (fmt[i] == 's') {
                        dest += _fmtstr(arguments[idx], num);
                        idx+=1;
                    }
                }
                break;
                default:
                    dest += '%';
                    break;
            }
        } else {
            dest += c;
        }
    }
    return dest;
}

window.sformat = sFormat;

function hex2num(hex) {
    var hexmap = HEXMAP;
    if(hex[0] == '0' && (hex[1] == 'X' || hex[1] == 'x')) {
        hex = hex.substr(2);
    }
    var num = 0;
    for(var i = 0; i < hex.length; i++) {
        var c = hex[i];
        num = num * 16;
        if (hexmap[c] == undefined) {
            throw 'invalid char ' + c;
        } else {
            num += hexmap[c];
        }
    }
    return num;
}


function stringStartsWith(chars) {
    return this.indexOf(chars) === 0;
}

String.prototype.startsWith = String.prototype.startsWith || stringStartsWith;

String.prototype.endsWith = String.prototype.endsWith || function (ends) {
    
    function _StrEndsWith(str, ends) {
        return str.lastIndexOf(ends) === (str.length - ends.length);
    } 
        
    if (!ends instanceof Array){
        return _StrEndsWith(this, ends);
    } else {
        for (var i = 0; i < ends.length; i++) {
            if (_StrEndsWith(this, ends[i])) {
                return true;
            }
        }
        return false;
    }
}


String.prototype.count = String.prototype.count || function (dst) {
    var count = 0;
    var start = 0;
    var index = -1;
    while ((index = this.indexOf(dst, start)) != -1) {
        count += 1;
        start = index + 1;
    }
    return count;
}

String.prototype.format = String.prototype.format || function () {
    var dest = "";
    var idx = 0;
    for(var i = 0; i < this.length; i++) {
        var c = this[i];
        if (c == '%') {
            switch (this[i+1]) {
                case 's':
                    i+=1;
                    dest += arguments[idx];
                    idx+=1;
                    break;
                case '%':
                    i+=1;
                    dest += '%';
                    break;
                default:
                    dest += '%';
                    break;
            }
        } else {
            dest += c;
        }
    }
    return dest;
}
/**
 * 生成重复的字符串
 * @param {number} count
 * @return string
 */
String.prototype.repeat = function (count) {
    var value = this;
    var str = "";
    for (var i = 0; i < count; i++) {
        str += value;
    }
    return str;
}


////////////////////////////////////////////////////////////////////////////
/**
 * Array 兼容增强包
 */
// 4.1 作为函数调用 Array 构造器
// 4.1.1 Array ( [ item1 [ , item2 [ , … ] ] ] )
// 4.2 Array 构造器
// 4.2.1 new Array ( [ item0 [ , item1 [ , … ] ] ] )
// 4.2.2 new Array (len)
// 4.3 Array 构造器的属性
// 4.3.1 Array.prototype
// 4.3.2 Array.isArray ( arg )
// 4.4 数组原型对象的属性
// 4.4.1 Array.prototype.constructor
// 4.4.2 Array.prototype.toString ( )
// 4.4.3 Array.prototype.toLocaleString ( )
// 4.4.4 Array.prototype.concat ( [ item1 [ , item2 [ , … ] ] ] )
// 4.4.5 Array.prototype.join (separator)
// 4.4.6 Array.prototype.pop ( )
// 4.4.7 Array.prototype.push ( [ item1 [ , item2 [ , … ] ] ] )
// 4.4.8 Array.prototype.reverse ( )
// 4.4.9 Array.prototype.shift ( )
// 4.4.10 Array.prototype.slice (start, end)
// 4.4.11 Array.prototype.sort (comparefn)
// 4.4.12 Array.prototype.splice (start, deleteCount [ , item1 [ , item2 [ , … ] ] ] )
//        arr.splice(2,0,item) ==> arr.insert(2, item)
// 4.4.13 Array.prototype.unshift ( [ item1 [ , item2 [ , … ] ] ] )
// 4.4.14 Array.prototype.indexOf ( searchElement [ , fromIndex ] )
// 4.4.15 Array.prototype.lastIndexOf ( searchElement [ , fromIndex ] )
// 4.4.16 Array.prototype.every ( callbackfn [ , thisArg ] )
// 4.4.17 Array.prototype.some ( callbackfn [ , thisArg ] )
// 4.4.18 Array.prototype.forEach ( callbackfn [ , thisArg ] )
// 4.4.19 Array.prototype.map ( callbackfn [ , thisArg ] )
// 4.4.20 Array.prototype.filter ( callbackfn [ , thisArg ] )
// 4.4.21 Array.prototype.reduce ( callbackfn [ , initialValue ] )
// 4.4.22 Array.prototype.reduceRight ( callbackfn [ , initialValue ] )
// 4.5 Array 实例的属性
// 4.5.1 [[DefineOwnProperty]] ( P, Desc, Throw )
// 4.5.2 length

/**
 * 判断数组中是否存在以start开头的字符串
 * @param {string} start
 */
Array.prototype.startsWith = Array.prototype.startsWith || function (start) {
    var array = this;
    for (var key in array) {
        var item = array[key];
        if (item.startsWith(start)) return true;
    }
    return false;
}

Array.prototype.each = Array.prototype.each || function (callback) {
    var self = this;
    for (var i = 0; i < self.length; i++) {
        var item = self[i];
        callback(i, item);
    }
}

/**
 * forEach遍历
 * @param {function} callback
 */
Array.prototype.forEach = Array.prototype.forEach || function (callback) {
    var self = this;
    for (var i = 0; i < self.length; i++) {
        var item = self[i];
        callback(item, i, self);
    }
}


/**
 * filter 函数兼容
 */
if (!Array.prototype.filter) {
  Array.prototype.filter = function(fun) {
    if (this === void 0 || this === null) {
      throw new TypeError();
    }

    var t = Object(this);
    var len = t.length >>> 0;
    if (typeof fun !== "function") {
      throw new TypeError();
    }

    var res = [];
    var thisArg = arguments.length >= 2 ? arguments[1] : void 0;
    for (var i = 0; i < len; i++) {
      if (i in t) {
        var val = t[i];
        // NOTE: Technically this should Object.defineProperty at
        //       the next index, as push can be affected by
        //       properties on Object.prototype and Array.prototype.
        //       But that method's new, and collisions should be
        //       rare, so use the more-compatible alternative.
        if (fun.call(thisArg, val, i, t))
          res.push(val);
      }
    }

    return res;
  };
}


/**
 * 日期格式化
 * @param {string} format 日期格式
 */
Date.prototype.format = Date.prototype.format || function (format) {
    var year = this.getFullYear();
    var month = this.getMonth() + 1;
    var day = this.getDate();
    var hour = this.getHours();
    var minute = this.getMinutes();
    var second = this.getSeconds();
    if (format == "yyyy-MM-dd") {
        return sFormat("%d-%2d-%2d", year, month, day);
    }
    if (format == "HH:mm:ss") {
        return sFormat("%2d:%2d:%2d", hour, minute, second);
    }
    return sFormat("%d-%2d-%2d %2d:%2d:%2d", year, month, day, hour, minute, second);
};


(function(){

    /**
     * part of quarkjs
     * 构造函数.
     * @name EventDispatcher
     * @class EventDispatcher类是可调度事件的类的基类，它允许显示列表上的任何对象都是一个事件目标。
     */
    var EventDispatcher = function()
    {
        //事件映射表，格式为：{type1:[listener1, listener2], type2:[listener3, listener4]}
        this._eventMap = {};
    };

    /**
     * 注册事件侦听器对象，以使侦听器能够接收事件通知。
     */
    EventDispatcher.prototype.addEventListener = function(type, listener)
    {
        var map = this._eventMap[type];
        if(map == null) map = this._eventMap[type] = [];
        
        if(map.indexOf(listener) == -1)
        {
            map.push(listener);
            return true;
        }
        return false;
    };

    /**
     * 删除事件侦听器。
     */
    EventDispatcher.prototype.removeEventListener = function(type, listener)
    {
        if(arguments.length == 1) return this.removeEventListenerByType(type);

        var map = this._eventMap[type];
        if(map == null) return false;

        for(var i = 0; i < map.length; i++)
        {
            var li = map[i];
            if(li === listener)
            {
                map.splice(i, 1);
                if(map.length == 0) delete this._eventMap[type];
                return true;
            }
        }
        return false;
    };

    /**
     * 删除指定类型的所有事件侦听器。
     */
    EventDispatcher.prototype.removeEventListenerByType = function(type)
    {
        var map = this._eventMap[type];
        if(map != null)
        {
            delete this._eventMap[type];
            return true;
        }
        return false;
    };

    /**
     * 删除所有事件侦听器。
     */
    EventDispatcher.prototype.removeAllEventListeners = function()
    {   
        this._eventMap = {};
    };

    /**
     * 派发事件，调用事件侦听器。
     */
    EventDispatcher.prototype.dispatchEvent = function(event)
    {
        var map = this._eventMap[event.type];
        if(map == null) return false;   
        if(!event.target) event.target = this;
        map = map.slice();

        for(var i = 0; i < map.length; i++)
        {
            var listener = map[i];
            if(typeof(listener) == "function")
            {
                listener.call(this, event);
            }
        }
        return true;
    };

    /**
     * 检查是否为指定事件类型注册了任何侦听器。
     */
    EventDispatcher.prototype.hasEventListener = function(type)
    {
        var map = this._eventMap[type];
        return map != null && map.length > 0;
    };

    //添加若干的常用的快捷缩写方法
    EventDispatcher.prototype.on = EventDispatcher.prototype.addEventListener;
    EventDispatcher.prototype.un = EventDispatcher.prototype.removeEventListener;
    EventDispatcher.prototype.fire = EventDispatcher.prototype.dispatchEvent;


    // xnote事件驱动
    if (window.xnote == undefined) {
        window.xnote = {};
    }

    xnote._eventDispatcher = new EventDispatcher();
    xnote.addEventListener = xnote.on = function (type, listener) {
        return xnote._eventDispatcher.addEventListener(type, listener);
    }

    xnote.dispatchEvent = xnote.fire = function (type, target) {
        var event = {type: type, target: target};
        return xnote._eventDispatcher.dispatchEvent(event);
    }
    
})();
/**
 * xnote专用ui
 * 依赖库
 *   jquery
 *   layer.js
 * @author xupingmao
 * @since 2017/10/21
 * @modified 2020/01/24 14:05:21
 */
var XUI = function(window) {
    // 处理select标签选中情况
    function initSelect() {
        $("select").each(function(index, ele) {
            var self = $(ele);
            var children = self.children();
            // 使用$.val() 会取到第一个select标签值
            var value = self.attr("value");
            for (var i = 0; i < children.length; i++) {
                var child = children[i];
                if (value == child.value) {
                    child.selected = "selected";
                }
            }
        });
    }

    function initCheckbox() {
        $("input[type=checkbox]").each(function(index, ele) {
            var self = $(ele);
            var value = self.attr("default-value");
            if (value == "on") {
                self.attr("checked", "checked");
            }
        })
    }

    function initRadio() {
        $("input[type=radio]").each(function(index, ele) {
            var self = $(ele);
            var value = self.attr("default-value");
            if (value == self.val()) {
                self.attr("checked", "checked");
            }
        });
    }

    function initXRadio() {
        $(".x-radio").each(function(index, element) {
            var self = $(element);
            var option = self.attr("data-option");
            var value = self.attr("data-value");
            if (value == option) {
                self.addClass("selected-link");
            }
        });
    }

    // 类似tab的超链接
    function initTabLink() {
        var hasActive = false;
        $(".x-tab").each(function(index, ele) {
            var link = $(ele).attr("href");
            var fullpath = location.href;

            if (fullpath.indexOf(link) >= 0) {
                $(ele).addClass("tab-link-active");
                hasActive = true;
            }
        });
        if (!hasActive) {
            $(".x-tab-default").addClass("tab-link-active");
        }
    }

    // 点击跳转链接的按钮
    $(".link-btn").click(function() {
        var link = $(this).attr("x-href");
        if (!link) {
            link = $(this).attr("href");
        }
        var confirmMessage = $(this).attr("confirm-message");
        if (confirmMessage) {
            var check = confirm(confirmMessage);
            if (check) {
                window.location.href = link;
            }
        } else {
            window.location.href = link;
        }
    })

    // 点击prompt按钮
    // <input type="button" class="prompt-btn" action="/rename?name=" message="重命名为" value="重命名">
    $(".prompt-btn").click(function() {
        var action = $(this).attr("action");
        var message = $(this).attr("message");
        var defaultValue = $(this).attr("default-value");
        var message = prompt(message, defaultValue);
        if (message != "" && message) {
            $.get(action + encodeURIComponent(message),
            function() {
                window.location.reload();
            })
        }
    });

    // 初始化表单控件的默认值
    function initDefaultValue(event) {
        initSelect();
        initCheckbox();
        initRadio();
        initXRadio();
        initTabLink();
    }

    // 初始化
    initDefaultValue();
    // 注册事件
    xnote.addEventListener("init-default-value", initDefaultValue);
};

$(document).ready(function() {
    XUI(window);
});

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

        // 图片太小了，进行放大
        var minsize = 150;
        if (imgarea[0] < minsize && imgarea[1] < minsize) {
          var ratio = Math.min(minsize/imgarea[0], minsize/imgarea[1]);
          imgarea[0] = imgarea[0]*ratio;
          imgarea[1] = imgarea[1]*ratio;
        }
        
        return [imgarea[0]+'px', imgarea[1]+'px']; 
      }(),
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
        +'<img src="'+ data[start].src +'" alt="'+ (data[start].alt||'') +'" layer-pid="'+ data[start].pid +'">'
        +'<div class="layui-layer-imgsee">'
          +(data.length > 1 ? '<span class="layui-layer-imguide"><a href="javascript:;" class="layui-layer-iconext layui-layer-imgprev"></a><a href="javascript:;" class="layui-layer-iconext layui-layer-imgnext"></a></span>' : '')
          +'<div class="layui-layer-imgbar" style="display:'+ (key ? 'block' : '') +'"><span class="layui-layer-imgtit"><a target="_blank" href="' + data[start].src +  '">'+ (data[start].alt||'') +'</a><em>'+ dict.imgIndex +'/'+ data.length +'</em></span></div>'
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
/** 
* 获取窗口的宽度
*/
function getWindowWidth() {
    if (window.innerWidth) {
        return window.innerWidth;
    } else {
        // For IE
        return Math.min(document.body.clientHeight, document.documentElement.clientHeight);
    }
}

function getWindowHeight() {
    if (window.innerHeight) {
        return window.innerHeight;
    } else {
        // For IE
        return Math.min(document.body.clientWidth, document.documentElement.clientWidth);
    }
}

/**
 * 判断是否是PC设备，要求width>=800 && height>=600
 */
window.isPc = function() {
    return getWindowWidth() >= 800;
}

// alias
window.isDesktop = window.isPc;

window.isMobile = function() {
    return ! isPc();
};/** 下拉组件
 * @since 2020/01/11
 * @modified 2020/01/22 00:29:27
 */

$(function () {
    // Dropdown 控件

    function toggleDropdown(e) {
        var target = e.target;
        var dropdownContent = $(target).next(".dropdown-content");
        dropdownContent.slideToggle("fast");

        $(".dropdown-content").each(function (index, element) {
            if (element != dropdownContent[0]) {
                $(element).slideUp(0);
            }
        })
    }

    $(".dropdown").click(function (e) {
        toggleDropdown(e);
    });

    $(".x-dropdown").click(function (e) {
        toggleDropdown(e);
    });

    $("body").on("click", function (e) {
        var target = e.target;
        if ($(target).hasClass("dropdown") || $(target).hasClass("dropdown-btn")) {
            return;
        }
        $(".dropdown-content").hide();
    });
});
/** photo.js, part of xnote-ui **/

$(function () {
  // 图片处理
  $("body").on('click', ".x-photo", function (e) {
        // console.log(e);
        var src = $(this).attr("src");
        var alt = $(this).attr("alt");
        console.log(src);

        var data = [];
        var imageIndex = 0;
        var target = e.target;

        $(".x-photo").each(function(index, el) {
          if (el == target) {
            imageIndex = index;
          }

          var src = $(el).attr("data-src");
          if (!src) {
            src = $(el).attr("src");
          }
          
          data.push({
            "alt": $(el).attr("alt"),
            "pid": 0,
            "src": src,
            "thumb": ""
          });
        });

        layer.photos({
            "photos": {
                  "title": "", //相册标题
                  "id": 123, //相册id
                  "start": imageIndex, //初始显示的图片序号，默认0
                  "data": data
                },
            "anim":5
        });
  });
});
/** audio.js, part of xnote-ui 
 * @since 2020/01/05
 * @modified 2020/01/21 20:13:34
 **/

$(function(e) {

    $("body").on("click", ".x-audio",
    function(e) {
        var src = $(this).attr("data-src");
        layer.open({
            type: 2,
            content: src,
            shade: 0
        });
    });

})/**
 * xnote的公有方法
 */
var BASE_URL = "/static/lib/webuploader";

if (window.xnote == undefined) {
    window.xnote = {};
}

/** 创建上传器 **/
window.xnote.createUploader = function(fileSelector, chunked) {
    if (fileSelector == undefined) {
        fileSelector = '#filePicker';
    }

    var upload_service;

    // 默认分片
    if (chunked == undefined) {
        chunked = false;
    }

    if (chunked) {
        upload_service = "/fs_upload/range";
    } else {
        // 不分片的上传服务
        upload_service = "/fs_upload";
    }

    return WebUploader.create({
        // 选完文件后，是否自动上传。
        auto: true,
        // swf文件路径
        swf: BASE_URL + '/Uploader.swf',
        // 文件接收服务端。
        server: upload_service,
        // 选择文件的按钮。可选。
        // 内部根据当前运行是创建，可能是input元素，也可能是flash.
        pick: fileSelector,
        // 需要分片
        chunked: chunked,
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
};

// 把blob对象转换成文件上传到服务器
window.xnote.uploadBlob = function(blob, prefix, successFn, errorFn) {
    var fd = new FormData();
    fd.append("file", blob);
    fd.append("prefix", prefix);
    fd.append("name", "auto");
    //创建XMLHttpRequest对象
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/fs_upload');
    xhr.onload = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                if (successFn) {
                    successFn(data);
                } else {
                    console.log(data);
                }
            } else {
                console.error(xhr.statusText);
            }
        };
    };
    xhr.onerror = function(e) {
        console.log(xhr.statusText);
    }
    xhr.send(fd);
};

window.xnote.requestUpload = function(fileSelector, chunked, successFn, errorFn) {
    if (fileSelector == undefined) {
        throw new Error("selector is undefined");
    }

    var loadingIndex = 0;
    var uploader = window.xnote.createUploader(fileSelector, chunked);

    // 当有文件添加进来的时候
    uploader.on('fileQueued',
    function(file) {
        // 添加文件
        console.log("file = " + file);
    });

    // 文件上传过程中创建进度条实时显示。
    uploader.on('uploadProgress',
    function(file, percentage) {
        // 进度条
    });

    uploader.on('uploadBeforeSend',
    function(object, data, headers) {
        data.dirname = "auto";
    })

    // 文件上传成功，给item添加成功class, 用样式标记上传成功。
    uploader.on('uploadSuccess',
    function(file, resp) {
        console.log("uploadSuccess", file, resp);

        layer.close(loadingIndex);

        successFn(resp);
    });

    // 文件上传失败，显示上传出错。
    uploader.on('uploadError',
    function(file) {
        layer.alert('上传失败');
        layer.close(loadingIndex);
    });

    // 完成上传完了，成功或者失败，先删除进度条。
    uploader.on('uploadComplete',
    function(file) {
        console.log("uploadComplete", typeof(file), file);
    });

    // 触发上传文件操作
    $(fileSelector).click();

    // 选择文件完毕
    $(fileSelector).on("change",
    function(event) {
        console.log(event);
        var fileList = event.target.files; //获取文件对象 
        if (fileList && fileList.length > 0) {
            uploader.addFile(fileList);
            loadingIndex = layer.load(2);
        }
        // 清空文件列表，不然下次上传会重复
        event.target.files = [];
    });
};

/** x-upload.js end **/
if (window.xnote == undefined) {
    window.xnote = {};
}

window.xnote.showDialog = function(title, html) {
    if (isMobile()) {
        var area = ['100%', '100%'];
    } else {
        var area = ['600px', '80%'];
    }

    return layer.open({
        type: 1,
        title: title,
        shadeClose: true,
        area: area,
        content: html,
        scrollbar: false
    });
}

// 询问函数，原生prompt的替代方案
xnote.prompt = function(title, defaultValue, callback) {
    if (layer && layer.prompt) {
        // 使用layer弹层
        layer.prompt({
            title: title,
            value: defaultValue,
            scrollbar: false,
            area: ['400px', '300px']
        },
        function(value, index, element) {
            callback(value);
            layer.close(index);
        })
    } else {
        var result = prompt(title, defaultValue);
        callback(result);
    }
};

// 确认函数
xnote.confirm = function(message, callback) {
    if (layer && layer.confirm) {
        layer.confirm(message,
        function(index) {
            callback(true);
            layer.close(index);
        })
    } else {
        var result = confirm(message);
        callback(result);
    }
};

// 警告函数
xnote.alert = function(message) {
    if (layer && layer.alert) {
        layer.alert(message);
    } else {
        alert(message);
    }
};

window.xnote.toast = function(message, time) {
    if (time == undefined) {
        time = 1000;
    }
    var maxWidth = $(document.body).width();
    var fontSize = 14;
    var toast = $("<div>").css({
        "margin": "0 auto",
        "position": "fixed",
        "left": 0,
        "top": "24px",
        "font-size": fontSize,
        "padding": "14px 18px",
        "border-radius": "4px",
        "background": "#000",
        "opacity": 0.7,
        "color": "#fff",
        "line-height": "22px",
        "z-index": 1000
    });
    toast.text(message);

    $(document.body).append(toast);
    var width = toast.outerWidth();
    var left = (maxWidth - width) / 2;
    if (left < 0) {
        left = 0;
    }
    toast.css("left", left);
    setTimeout(function() {
        toast.remove();
    },
    time);
}

// 兼容之前的方法
window.showToast = window.xnote.toast;


// 自定义的dialog
$(function () {
    // 点击激活对话框的按钮
    $(".dialog-btn").click(function() {
        var dialogUrl = $(this).attr("dialog-url");
        var dialogId = $(this).attr("dialog-id");
        if (dialogUrl) {
            // 通过新的HTML页面获取dialog
            $.get(dialogUrl, function(respHtml) {
                $(document.body).append(respHtml);
                doModal(dialogId);
                // 重新绑定事件
                xnote.fire("init-default-value");
                $(".x-dialog-close, .x-dialog-cancel").unbind("click");
                $(".x-dialog-close, .x-dialog-cancel").on("click",
                function() {
                    onDialogHide();
                });
            })
        }
    });


    /**
     * 初始化弹层
     */
    function initDialog() {
        // 初始化样式
        $(".x-dialog-close").css({
            "background-color": "red",
            "float": "right"
        });

        $(".x-dialog").each(function(index, ele) {
            var self = $(ele);
            var width = window.innerWidth;
            if (width < 600) {
                dialogWidth = width - 40;
            } else {
                dialogWidth = 600;
            }
            var top = Math.max((getWindowHeight() - self.height()) / 2, 0);
            var left = (width - dialogWidth) / 2;
            self.css({
                "width": dialogWidth,
                "left": left
            }).css("top", top);
        });

        $("body").css("overflow", "hidden");
    }

    /**
   * 隐藏弹层
   */
    function onDialogHide() {
        $(".x-dialog").hide();
        $(".x-dialog-background").hide();
        $(".x-dialog-remote").remove(); // 清空远程的dialog
        $("body").css("overflow", "auto");
    }

    $(".x-dialog-background").click(function() {
        onDialogHide();
    });

    $(".x-dialog-close, .x-dialog-cancel").click(function() {
        onDialogHide();
    });

    function doModal(id) {
        initDialog();
        $(".x-dialog-background").show();
        $(".x-dialog-remote").show();
        $("#" + id).show();
    }

});
/**
 * 通用的操作函数
 */
$(function() {

  // 设置最小的高度
  $(".root").css("min-height", getWindowHeight());

  window.moveTo = function (selfId, parentId) {
      $.post("/note/move", 
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
        var width = $(".root").width() - 40;
        var area;

        if (isMobile()) {
          area = ['100%', '100%'];
        } else {
          width = 600;
          area = [width + 'px', '80%'];
        }
        
        layer.open({
          type: 1,
          title: "移动笔记",
          shadeClose: true,
          area: area,
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
      var mainWidth = $(".root").width();
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

    window.openFileOption = function (e) {
      console.log(e);
      var path = $(e).attr("data-path");
      openDialog("/fs_api/plugins?embed=true&path=" + path);
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
      $(selector).css("height", height).css("overflow", "auto");
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

window.ContentDialog = {
  open: function (title, content, size) {
    var width = $(".root").width() - 40;
    var area;

    if (isMobile()) {
      area = ['100%', '100%'];
    } else {
      if (size == "small") {
        area = ['400px', '300px'];        
      } else {
        area = [width + 'px', '80%'];
      }
    }

    layer.open({
      type: 1,
      shadeClose: true,
      title: title,
      area: area,
      content: content,
      scrollbar: false
    });
  }
}
