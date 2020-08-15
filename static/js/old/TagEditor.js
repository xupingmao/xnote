
function TagEditor(containerId, relatedText, splitText, resultId) {
    var self = this;
    self.resultId = resultId;
    self.useUpperCase = false;
    
    function clearArray(array) {
        var newArray = [];
        for (var i = 0; i < array.length; i++) {
            if (array[i]) {
                newArray.push(array[i]);
            }
        }
        return newArray;
    }
    
    function initRelatedNamesEditor(names) {
        var container = document.getElementById(containerId);
        container.innerHTML = '';
        for (var i = 0; i < names.length; i++) {
            var name = names[i];
            var span = document.createElement("span");
            span.innerHTML = name;
            var btn = document.createElement('button');
            // link.href = 'javascript:delRelated("$name")'.replace('$name', name);
            btn.addEventListener('click', (function (name) {
                return function () {delRelated(name)};
            })(name));
            btn.innerHTML = 'X';
            container.appendChild(span);
            container.appendChild(btn);
        }
        var btn = document.createElement('button');
        var space = document.createElement("span");
        space.innerHTML = "&nbsp;&nbsp;"
        container.appendChild(space);
        
        var input = document.createElement('input');
        input.id = "newRelated";
        container.appendChild(input);
        
        btn.addEventListener('click', addRelated);
        btn.innerHTML = '+';
        container.appendChild(btn);
        
        var result = document.createElement("input");
        result.id = self.resultId;
        result.value = splitText + self.relatedNames.join(splitText) + splitText;
        result.style.display="none";
        container.appendChild(result);
    }
    
    function initRelatedNamesEditor2(names) {
        var container = document.getElementById(containerId);
        container.innerHTML = '';
        var table = document.createElement('table');
        for (var i in names) {
            var tr = document.createElement('tr');
            var td1 = document.createElement('td');
            var td2 = document.createElement('td');
            var name = names[i];
            var span = document.createElement('span');
            span.innerHTML = name;
            var btn = document.createElement('button');
            // link.href = 'javascript:delRelated("$name")'.replace('$name', name);
            btn.addEventListener('click', (function (name) {
                return function () {delRelated(name)};
            })(name));
            btn.innerHTML = 'del';
            td1.appendChild(span);
            td2.appendChild(btn);
            tr.appendChild(td1);
            tr.appendChild(td2);
            table.appendChild(tr);
        }
        var tr = document.createElement('tr');
        var td1 = document.createElement('td');
        var td2 = document.createElement('td');
        var input = document.createElement('input');
        input.id = "newRelated";
        var btn = document.createElement('button');
        btn.addEventListener('click', addRelated);
        btn.innerHTML = 'add';
        td1.appendChild(input);
        td2.appendChild(btn);
        tr.appendChild(td1);
        tr.appendChild(td2);
        table.appendChild(tr);
        container.appendChild(table);
        
        var result = document.createElement("input");
        result.id = self.resultId;
        result.value = splitText + self.relatedNames.join(splitText) + splitText;
        result.style.display="none";
        container.appendChild(result);
    }
    function delRelated(name) {
        var relatedNames = self.relatedNames;
        var index = relatedNames.indexOf(name);
        if (index >= 0) {
            relatedNames.splice(index, 1);
            initRelatedNamesEditor(relatedNames);
        }
    }
    function addRelated() {
        var relatedNames = self.relatedNames;
        var input = document.getElementById('newRelated');
        var name = input.value;
        if (name == '') {
            alert("can not add empty tag!");
            return;
        }
        if (self.useUpperCase) {
            name = name.toUpperCase();
        }
        var index = relatedNames.indexOf(name);
        if (index >= 0) {
            alert("name " + name + " exists!");
        } else {
            relatedNames.push(name);
            initRelatedNamesEditor(relatedNames);
        }
    }
    
    this.getRelatedNames = function () {
        return this.relatedNames;
    }
    
    this.setCaseSensitive = function (flag) {
        self.useUpperCase = flag;
    }
    
    this.setUpperCase = function (flag) {
        this.useUpperCase = flag;
    }
    
    var relatedNames = relatedText.split(splitText);
    relatedNames = clearArray(relatedNames);
    self.relatedNames = relatedNames;
    initRelatedNamesEditor(relatedNames);
}
