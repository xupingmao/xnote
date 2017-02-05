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

String.prototype.startsWith = String.prototype.startsWith || function (starts) {
    throw ("not implemented");
}

String.prototype.endsWith = String.prototype.endsWith || function (ends) {
    
    function _StrEndsWith(str, ends) {
        var str = this;
        for (var i = ends.length-1, j = str.length - 1; i >= 0; i--, j--) {
            if (str[j] != ends[i]) {
                return false;
            }
        }
        return true;
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
 * @param count int
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