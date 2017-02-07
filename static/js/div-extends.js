(function () {
    document.onreadystatechange = function () {
        if(document.readyState == "complete"){
            var divs = document.getElementsByTagName('div');
            for (var i in divs) {
                var div = divs[i];
                if (div.attributes && div.attributes['role'] && div.attributes['role'].nodeValue == 'text') {
                    var text = div.innerHTML;
                    div.innerHTML = text.replace(/\n/gi, '<br/>');
                }
            }
        }
    } 
})()