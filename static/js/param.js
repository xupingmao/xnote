
function parse_param(src) {
    var path = '';
    var args = {};
    var state = 0; //  path 
    var name = '';
    var value = '';
    for(var i = 0; i < src.length; i++) {
        var c = src[i]
        if (c == '?' || c == '&') {
            state = 1; // arg name;
            if (name != '') {
                args[name] = value; 
            }
            name = '';
            continue;
        } else if (c == '=') { // arg value
            state = 2; 
            value = '';
            continue;
        }
        if (state == 0) {
            path += c; // path state
        } else if (state == 1) {
            name += c; // arg name;
        } else if (state == 2) {
            value += c;
        }
    }
    if (name != '') {
        args[name] = value;
    }
    return {'path': path, 'param': args};
}

