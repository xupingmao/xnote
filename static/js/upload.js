(function (window) {
    // check whether browser support HTML5 file API

    if (!window.FileReader) {
        return;
    }

    function handleFiles (files) {
        if (files.length) {
            var file = files[0];
            var reader = new FileReader();  
            reader.onload = function()  
            {  
                document.getElementById("filecontent").innerHTML = this.result;  
            };  
            reader.readAsText(file);  
        }
    }
})(window);