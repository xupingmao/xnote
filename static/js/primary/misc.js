// @author xupingmao
// @since 2017/08/16
// @modified 2020/07/04 16:45:18

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
