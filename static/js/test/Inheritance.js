
function Person (_name) {
    
    this.name = _name;
    this.talk = function () {
        console.log("my name is " + this.name);
    }
}

Person.prototype.laugh = function () {
    console.log("haha~~");
}

function Chinese () {
    
}

Chinese.prototype = Person;

var person = new Person("English");
var chinese = new Chinese("Chinese");

function tryRun (func, args) {
    try {
        console.log("try to run " + func.name + "");
        func();
    } catch (e) {
        if (func != undefined) {
            console.log("fail to run " + func.name);
        } else {
            console.log("function is undefined");
        }
    }
}

tryRun(person.talk);
tryRun(chinese.talk);
tryRun(person.laugh);
tryRun(chinese.laugh);