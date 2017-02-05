function getRadioValue(name) {
    var radios = document.getElementsByName(name);
    for (var i = 0; i < radios.length; i++) {
        var radio = radios[i];
        if (radio.checked) return radio.value;
    }
    return undefined;
}