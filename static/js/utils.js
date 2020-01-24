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

