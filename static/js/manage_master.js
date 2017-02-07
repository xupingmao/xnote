requirejs.config({
    baseUrl:"static/js",
});

// var menuInitialized = false;
// finalily give up the method.
// requirejs(['webos/StringPrototype'], function(mod) {
//     initMenu(menu);
// });

function initMenu(menu) {
    var menuElement = $("#menu");
    for(var i = 0; i < menu.length; i++) {
        var item = menu[i];
        var id = "m_" + item.id;
        var text = item.text;
        var href = item.href;
        var cl = item.cl;
        var fmt;
        var newElement;
        if (cl == undefined) {
            fmt = "<li id=\"%s\"><a href=\"%s\">%s</a></li>";
            newElement = fmt.format(id, href, text);
        } else {
            fmt = "<li id=\"%s\" class=\"%s\">%s</li>";
            newElement = fmt.format(id, cl, text);
        }
        menuElement.append(newElement);
    }
}

function activeMenu2(activeMenuId){
    if (activeMenuId) {
        var ele = $("#m_" + activeMenuId);
        // console.log(ele, ele.length);
        if (ele.length > 0) {
            ele.addClass('active');
            // activeMenuId = undefined;
        } else {
            // when activeMenuId is a global variable, called by setTimeout, the value of
            // activeMenuId will be undefined, I don't know why.
            setTimeout("activeMenu2('%s')".format(activeMenuId), 10);
        }
    } 
}
function activeMenu(id) {
    activeMenu2(id);
    setTitle(id);
}

$(function () {
    initMenu(menu);
    var m = getConf(location.href, "menu");
    if (m) {
        activeMenu(m);
    } else {
        var _menu = $("#_menu");
        if (_menu.length != 0) {
            var id = _menu.val();
            activeMenu(id);
        }
    }

})