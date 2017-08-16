
var getUrlParams = function()
{
    var params = {};
    var url = window.location.href;
    var idx = url.indexOf("?");
    if(idx > 0)
    {
        var queryStr = url.substring(idx + 1);
        var args = queryStr.split("&");
        for(var i = 0, a, nv; a = args[i]; i++)
        {
            nv = args[i] = a.split("=");
            params[nv[0]] = nv.length > 1 ? nv[1] : true;
        }
    }
    return params;
};


