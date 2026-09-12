// load css by userAgent
(function () {
    var UA = navigator.userAgent.toLowerCase();
    var link = document.createElement("link");
    link.rel = "stylesheet";
    //alert(UA);
    if (UA.indexOf("iphone") >= 0 || UA.indexOf("android") >= 0) {
        link.href="/css/home.mobile.css";
    } else if (UA.indexOf("ipad") >= 0) {
        link.href="/css/home.tablet.css";
    } else {
        link.href="/css/home.css";
    }
    document.head.appendChild(link);
}) ();
