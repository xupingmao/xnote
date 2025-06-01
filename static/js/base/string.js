// @author xupingmao
// @since 2017/08/16
// @modified 2021/07/04 13:54:23

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


function num2hex(num) {

}

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
        '8':8, '9':9, '0':0,
    };

function _strfill(len, c) {
    c = c || ' ';
    s = "";
    for(var i = 0; i < len; i++) {
        s += c;
    }
    return s;
}

function _fmtnum(numval, limit) {
    var max = Math.pow(10, limit);
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
        var zeros = limit - cnt;
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
                    var num = 0;
                    i += 1;
                    while (hexmap[fmt[i]] != undefined) {
                        num = num * 10 + hexmap[fmt[i]];
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
                        dest += _fmtnum(val, num);
                    } else if (fmt[i] == 's') {
                        dest += _fmtstr(arguments[idx], num);
                        idx+=1;
                    }
                    i+=1;
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
 * @param {int} count
 * @return {string}
 */
String.prototype.repeat = function (count) {
    var value = this;
    var str = "";
    for (var i = 0; i < count; i++) {
        str += value;
    }
    return str;
}

/**
 * 访问字符串的某个下标字符
 * @param {int} index
 * @return {string}
 */
String.prototype.Get = function (index) {
    if (index >= 0) {
        return this[index];
    } else {
        var realIndex = this.length + index;
        return this[realIndex];
    }
}

/**
 * 简单的模板渲染，这里假设传进来的参数已经进行了html转义
 */
function renderTemplate(templateText, object) {
    return templateText.replace(/\$\{(.*?)\}/g, function (context, objKey) {
        return object[objKey.trim()] || '';
    });
}

/**
 * 原型：字符串格式化
 * @param args 格式化参数值
 */
// String.prototype.format = function(args) {
//     var result = this;
//     if (arguments.length < 1) {
//         return result;
//     }

//     var data = arguments; // 如果模板参数是数组
//     if (arguments.length == 1 && typeof (args) == "object") {
//         // 如果模板参数是对象
//         data = args;
//     }
//     return result.replace(/\{(.*?)\}/g, function (context, objKey) {
//         return object[objKey.trim()] || '';
//     });
// }

