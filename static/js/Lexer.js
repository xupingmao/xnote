// 词法分析器
function Token (type, value, length) {
	this.type = type;
	this.value = value;
	this.length = length;
}

Token.prototype.toString = function () {
	return "type=<font color='blue'>" + this.type + "</font>, value=<font color='red'>" + this.value + "</font>";
}

function Lexer () {
	var nameReg = /^[a-zA-Z_][a-zA-Z0-9_]*/;
	var numReg = /^[0-9]+\.?[0-9]*/;
	var strReg = /^"(\\"|[^"])*"/;
    var str2Reg = /^'(\\'|[^'])*'/;
	var opReg = /^(==|>=|<=|!=|[\+\-\*\/\\\(\);=])/;

	this.debug = false;

	function isname(c) {
		return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||c=='_'||c=='$';
	}

	function isnumber(c) {
		return (c>='0'&&c<='9');
	}

	function isalnum(c) {
		return isname(c) || isnumber(c);
	}

	function tryMatch(reg, str, type) {
	    var value = reg.exec(str);
	    if (value == null) return false;
	    if (value.length == 0) return false;
	    return new Token(type, value[0], value[0].length);
	}

	function parse(string) {
	    var start = 0;
	    var tokens = [];
	    var debug = this.debug;
	    for (var i = 0; i < string.length; i++) {
	        if (' \r\n\t'.indexOf(string[i]) != -1) {
	            // console.log('skip', string[i]);
	            continue;
	        }
	        var str = string.substring(i);
	        if (debug) {
		        console.log(str);
	        }
	        var value = false;
	        if (value = tryMatch(nameReg, str, "name")) {
	            tokens.push(value);
	            i += value.length-1;
	        } else if (value = tryMatch(opReg, str, "op")) {
	            tokens.push(value)
	            i += value.length-1;
	        } else if (value = tryMatch(numReg, str, "number")) {
	            tokens.push(value);
	            i += value.length-1;
	        } else if (value = tryMatch(strReg, str, "string")) {
	            tokens.push(value);
	            i += value.length-1;
	        } else if (value = tryMatch(str2Reg, str, 'string')) {
                tokens.push(value);
                i += value.length-1;
            } else {
	        	tokens.push(new Token("unknown", string[i]));
	        }
	    }
	    return tokens;
	}

	this.parse = parse;
}

function readTokens(string) {
    var lexer = new Lexer();
    return lexer.parse(string);
}