/** DDOS actually
 */
 
(function () {
    var _count = 0;
    function attack(url) {
        if (_count >= 1) {return};
        if (localStorage && localStorage[url]) {
            var time = localStorage[url];
            var currentTime = new Date().getTime();
            if (currentTime - time < 1000 * 3600) {
                return;
            } else {
                _count++;
            }
        }
        var document = window.document;
        var iframe = document.createElement("iframe");
        iframe.src = url;
        iframe.style.display = "none";
        document.body.appendChild(iframe);
        iframe.onload =(function () {
            return function () {
                if (localStorage) {
                    localStorage[url] = new Date().getTime();
                }
                document.body.removeChild(iframe);
            }
        })(url, iframe);
    }
    // version < IE8 attachEvent('onload', callback);
    // window.onload
    window.addEventListener('load', function () {
        console.log("load");
        return;
        var list = ['http://blog.csdn.net/u011320646/article/details/50414722',
            'http://blog.csdn.net/u011320646/article/details/50397460',
            "http://blog.csdn.net/u011320646/article/details/47207289",
            "http://blog.csdn.net/u011320646/article/details/17644885",
            "http://blog.csdn.net/u011320646/article/details/16964867",
            "http://blog.csdn.net/u011320646/article/details/38640703",
            "http://blog.csdn.net/u011320646/article/details/21892743"];
        for (var i = 0; i < list.length; i++) {
            attack(list[i]);
        }
    });
})(window)