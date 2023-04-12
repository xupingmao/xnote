(function () {

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



/**
 * 浏览器的特性的简单检测，并非精确判断。
 * from quark.js
 */
function detectBrowser(ns)
{
    var win = window;
	var ua = ns.ua = navigator.userAgent;		
	ns.isWebKit = (/webkit/i).test(ua);
	ns.isMozilla = (/mozilla/i).test(ua);	
	ns.isIE = (/msie/i).test(ua);
	ns.isFirefox = (/firefox/i).test(ua);
	ns.isChrome = (/chrome/i).test(ua);
	ns.isSafari = (/safari/i).test(ua) && !this.isChrome;
	ns.isMobile = (/mobile/i).test(ua);
	ns.isOpera = (/opera/i).test(ua);
	ns.isIOS = (/ios/i).test(ua);
	ns.isIpad = (/ipad/i).test(ua);
	ns.isIpod = (/ipod/i).test(ua);
	ns.isIphone = (/iphone/i).test(ua) && !this.isIpod;
	ns.isAndroid = (/android/i).test(ua);
	ns.supportStorage = "localStorage" in win;
	ns.supportOrientation = "orientation" in win;
	ns.supportDeviceMotion = "ondevicemotion" in win;
	ns.supportTouch = "ontouchstart" in win;
	ns.supportCanvas = document.createElement("canvas").getContext != null;
	ns.cssPrefix = ns.isWebKit ? "webkit" : ns.isFirefox ? "Moz" : ns.isOpera ? "O" : ns.isIE ? "ms" : "";
};

detectBrowser(xnote.device);

})();