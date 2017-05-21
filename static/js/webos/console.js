
function History() {
    this.max = 10;
    this.data = [];
    this.cur = 0;
}

History.prototype.add = function (data) {
    if (this.data.length > this.max) {
        this.data.shift(0);
    }
    this.data.push(data);
}

History.prototype.before = function () {
    if (this.data.length == 0) {
        return "";
    }
    if (this.cur == 0) {
        this.cur = this.data.length-1;
    } else {
        this.cur -= 1;
    }
    return this.data[this.cur];
}

History.prototype.after = function () {
    if (this.data.length == 0) {
        return "";
    }
    if (this.cur == this.data.length - 1) {
        this.cur = 0;
    } else {
        this.cur += 1;
    }
    return this.data[this.cur];
}
/** webos console class
 *  
 *   callback (inputStr, response);
 *     response is a function, response(result)
 */
function WebOSConsole(id, opt, callback) {
    var rows = 20;
    var cols = 40;
    var debug = false;


    if (opt != undefined) {
        rows = opt.rows || rows;
        cols = opt.cols || cols;
        debug = opt.debug || false;
    }
    this.rows = rows;
    this.cols = cols;

    var line = "";
    var linecnt = 1;
    var headline = {text:""};
    var curline = headline;
    var path = "/";

    var div = $("#"+id)[0];

    var cursorState = 0;
    
    var buf = "";

    // stdin or in application.
    var mode;

    // instance of webosconsole;
    var instance = this;

    var iswaiting = false;

    var history = new History();
    window.h = history;

    function updateCursor() {
        var cursorEle = $("#cursor")[0];
        if (cursorState==0) {
            cursorState = 1;
        } else {
            cursorState = 0;
        }

        if (!cursorState) {
            text = "";
        } else {
            text = "&nbsp;";
        }
        cursorEle.innerHTML = text;
    }

    function newline() {
        if (linecnt >= rows) {
            headline = headline.next;
            headline.prev = undefined;
        } else {
            linecnt += 1;
        }
        curline.next = {};
        curline.next.prev = curline;
        curline = curline.next;
        line = "";
        curline.text = "";
        update();
    }

    function filter(text) {
        var newtext = "";
        for(var i = 0; i < text.length; i++) {
            if (text[i] == ' ') {
                newtext += '&nbsp;';
            } else if (text[i] == '<') {
                newtext += '&lt;';
            } else if (text[i] == '>') { 
                newtext += '&gt;';
            } else {
                newtext += text[i];
            }
        }
        return newtext;
    }

    function update() {
        var iter = headline;
        var text = "";
        while (iter != undefined) {
            text += "<span class='console_text'>"+filter(iter.text)+"</span>";
            iter = iter.next;
            if (iter != undefined) {
                text += '<br/>'
            }
        }
        div.innerHTML = text + "<span id='cursor' class='console_text'></span>";
    }

    function write(c) {
        if (c == '\r') {
            return;
        }
        if (c == '\n') {
            newline();
            line = c;
        }
        if (line.length < cols) {
            line += c;
        } else {
            newline();
            line = c;
        }
        curline.text = line;
        update();
        buf += c;
    }

    function writeString(str) {
        for(var i = 0; i < str.length; i++) {
            write(str[i]);
        }
    }

    function writeline(str) {
        writeString(str);
        newline();
    }

    function writeHead() {
        writeString("$");
        writeString(path+"> ");
        buf = "";
    }

    function backspace0() {
        if (buf.length == 0) {
            return;
        } else {
            buf = buf.substr(0, buf.length-1);
        }
        if (line.length == 0) {
            // is the first line
            if (curline.prev == undefined) {
                line = "";
            } else {
                curline = curline.prev;
                curline.next = undefined;
                line = curline.text;
                linecnt -= 1;
            }
        }
        line = line.substr(0, line.length-1);
        curline.text = line;
    }

    function backspace() {
        backspace0();
        update();
    }

    function clearbuf() {
        while (buf.length > 0) {
            backspace0();
        }
        update();
    }

    function getChar(event) {
        return String.fromCharCode(event.charCode);
    }

    function response(result) {
        iswaiting = false;
        writeline(result);
        buf = "";
        writeHead(); 
    }

    function consoleEOF() {
        newline();
        // the console is blocked.
        if (iswaiting) {
        } else {
            if (buf == "") {
                buf = "";
                writeHead();
            } else {
                console.log(buf);
                history.add(buf);
                // var rs = webosExec(buf, undefined, instance);
                // block the console in the execution
                iswaiting = true;
                var rs = callback(buf, response)
            }
        }
    }

    this.wait = function () {
        iswaiting = true;
    }

    this.resume = function () {
        iswaiting = false;
        buf = "";
        newline();
        writeHead();
    }

    this.writeline = writeline;
    this.writeString = writeString;

    window.onkeydown = function (event) {
        var keyCode = event.keyCode;
        var disable = true;
        if (debug) {
            console.log(keyCode);
        }
        if (keyCode == 8) {
            backspace();
        } else if (keyCode == 13) {
            consoleEOF();
        } else if (keyCode == 32) {
            write(' ');
        } else if (keyCode == 38) {
            // arrow up
            clearbuf();
            writeString(history.before());
            update();
        } else if (keyCode == 40) {
            // arrow down
            clearbuf();
            writeString(history.after());
            update();
        } else {
            disable = false;
        }

        if(disable) {
            if (event.stopPropagation) {
                event.stopPropagation();
            }
            if (event.preventDefault) {
                event.preventDefault();
            }

            event.keyCode = 0;
            event.returnValue = false;
        }
    }

    // should use input or textarea
    window.onkeypress = function (event) {
        // console.log(event, event.keyCode, String.fromCharCode(event.keyCode));
        var keyCode = event.keyCode;
        console.log(event.keyCode);
        var c = getChar(event);
        write(c);
    }

    this.state = 0;
    this.start = function() {
        if (this.state == 0) {
            writeHead();
            update();

            // function loop() {
            //     updateCursor();
            //     setTimeout(loop, 500);
            // }

            // loop();

            setInterval(updateCursor, 500);
            this.state = 1;
        }
    }

    /**
     * 显示字符
     * @param {string} message
     */
    WebOSConsole.prototype.echo = function(message) {
        this.writeline(message);
    }
}