(function () {
    xnote.csv = {};

    var _isMacOS = navigator.userAgent.indexOf("Mac OS") >= 0;
    function isMacOS() {
        return _isMacOS;
    }

    if (isMacOS()) {
        console.log("Mac OS");
    }

    function getCharWidth(c) {
        if (!c) {
            return 0;
        }
        var code = c.charCodeAt(0);
        if (code > 127) {
            if (isMacOS()) {
                // Mac是个奇葩, 3个汉字5个宽度
                return 1.66;
            }
            return 2;
        }
        return 1;
    }


    function getStringWidth(str) {
        if (!str) {
            return 0;
        }
        var width = 0;
        for (var i = 0; i < str.length; i++) {
            width += getCharWidth(str[i]);
        }
        return Math.round(width);
    }
    
    
    String.prototype.padLeft = function (size, value) {
        // return _padding.substring(0, size-this.length) + this;
        var text = this;
        while (getStringWidth(text) < size) {
            text += value;
        }
        return text;
    }

    function formatCode(code) {
        // 格式化csv代码
        var rows = CSV.parse(code);
        var result = "";
        var gapSize = 5;
        var widthMap = {};
    
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            for (var j = 0; j < row.length; j++) {
                // calculate max width
                var cell = row[j];
                if (cell === undefined) {
                    cell = "-";
                }
                cell = cell.trim();
                var cellWidth = getStringWidth(cell) + gapSize;
                var oldWidth = widthMap[j];
                if (oldWidth === undefined) {
                    widthMap[j] = cellWidth;
                } else {
                    widthMap[j] = Math.max(oldWidth,cellWidth);
                }
            }
        }

        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            for (var j = 0; j < row.length; j++) {
                // calculate max width
                var cell = row[j];
                if (cell === undefined) {
                    cell = "-";
                }
                cell = cell.trim();
                var cellWidth = widthMap[j] || gapSize;
                result += cell.padLeft(cellWidth, " ");
                if (j != row.length-1) {
                    result += ",";
                } else {
                    result += "\n";
                }
            }
        }

        return result;
    }

    xnote.csv.formatCode = formatCode;

})();
