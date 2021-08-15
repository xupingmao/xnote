// @author xupingmao
// @since 2017/08/16
// @modified 2021/08/15 12:19:12

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
        if (item === start) return true;
    }
    return false;
}

// Array.prototype.each = Array.prototype.each || function (callback) {
//     var self = this;
//     for (var i = 0; i < self.length; i++) {
//         var item = self[i];
//         callback(i, item);
//     }
// }

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

