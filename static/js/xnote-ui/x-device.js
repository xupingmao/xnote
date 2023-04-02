/** 
* 获取窗口的宽度
*/
xnote.getWindowWidth = function() {
    if (window.innerWidth) {
        return window.innerWidth;
    } else {
        // For IE
        return Math.min(document.body.clientHeight, document.documentElement.clientHeight);
    }
}

window.getWindowWidth = xnote.getWindowWidth;

// 获取窗口的高度
xnote.getWindowHeight = function() {
    if (window.innerHeight) {
        return window.innerHeight;
    } else {
        // For IE
        return Math.min(document.body.clientWidth, document.documentElement.clientWidth);
    }
}

window.getWindowHeight = xnote.getWindowHeight

/**
 * 判断是否是PC设备，要求width>=800 && height>=600
 */
xnote.isDesktop = function() {
    return getWindowWidth() >= 800;
}

// alias
window.isPc = xnote.isDesktop;
window.isDesktop = window.isDesktop;

window.isMobile = function() {
    return !isPc();
};

xnote.isMobile = function() {
    return $(window).width() < xnote.MOBILE_MAX_WIDTH;
};
