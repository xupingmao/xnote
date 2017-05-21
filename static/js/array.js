/**
 * Array 兼容增强包
 */
Array.prototype.startsWith = Array.prototype.startsWith || function (dst) {
    var array = this;
    for (var key in array) {
        var item = array[key];
        if (item.startsWith(dst)) return true;
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
 * @param callback
 */
Array.prototype.forEach = Array.prototype.forEach || function (callback) {
    var self = this;
    for (var i = 0; i < self.length; i++) {
        var item = self[i];
        callback(item, i, self);
    }
}