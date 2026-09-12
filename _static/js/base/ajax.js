
function _doAjax(method, url, data, fnSuccess, fnFail) {
    var requestObj;
    if (window.XMLHttpRequest) {
        requestObj = new XMLHttpRequest();
    } else {
        requestObj = new ActiveXObject('Microsoft.XMLHTTP');
    }

    if (fnSuccess) {
        requestObj.open(method, url, true); // async
    } else {
        requestObj.open(method, url, false); // sync
    }
    requestObj.send(data)
    requestObj.onreadystatechange = function () {  //OnReadyStateChange
        if (requestObj.readyState == 4) {  // compelte
            if (requestObj.status == 200) {    //200
                if (fnSuccess) {
                    fnSuccess(requestObj.responseText);
                } else {
                    return requestObj.responseText;
                }
            } else {
                if (fnFail) {
                    fnFail();
                } else {
                    return;
                }
            }
        }
    };

}

function ajaxGet(url, fnSuccess, fnFail) {
    _doAjax("GET", url, null, fnSuccess, fnFail);
}

function ajaxPost(url, data, fnSuccess, fnFail) {
    _doAjax("POST", url, data, fnSuccess, fnFail);
}

function ajax(method, url, data, fnSuccess, fnFail) {
    _doAjax(method, url, data, fnSuccess, fnFail);
}