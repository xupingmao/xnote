function select(ident) {
    if (ident[0]=='#') {
        return document.getElementById(ident.substring(1));
    }
    if (ident[0]=='.') {
        return document.getElementsByClassName(ident.substring(1));
    }
}