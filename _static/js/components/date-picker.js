var DatePicker = {};

DatePicker.formatDate = function (year, month) {
    if (month == "0") {
        return year;
    }
    if (month < 10) {
        return year + "-0" + month;
    }
    return year + "-" + month;
}

DatePicker.getPrevMonth = function(year, month) {
    if (month > 1) {
        return this.formatDate(year, month - 1);
    } else {
        return this.formatDate(year - 1, 12);
    }
}

DatePicker.getNextMonth = function(year, month) {
    if (month < 12) {
        return this.formatDate(year, month + 1);
    } else {
        return this.formatDate(year + 1, 1);
    }
}

DatePicker.getCurrentMonth = function() {
    var year  = parseInt("{{year}}");
    var month = parseInt("{{month}}");
    return formatDate(year, month);
}
