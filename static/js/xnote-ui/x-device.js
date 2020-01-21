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
};