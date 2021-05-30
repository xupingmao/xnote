/**
 * xnote扩展事件
 * @author xupingmao
 * @since 2021/05/30 14:39:39
 * @modified 2021/05/30 14:42:56
 * @filename x-event.js
 */

// xnote事件驱动
if (window.xnote == undefined) {
    window.xnote = {};
}


(function(){

    /**
     * part of quarkjs
     * 构造函数.
     * @name EventDispatcher
     * @class EventDispatcher类是可调度事件的类的基类，它允许显示列表上的任何对象都是一个事件目标。
     */
    var EventDispatcher = function()
    {
        //事件映射表，格式为：{type1:[listener1, listener2], type2:[listener3, listener4]}
        this._eventMap = {};
        //事件注册表，格式为: {type1:文字说明, type2:文字说明}
        this._eventDescription = {};
    };

    /**
     * 注册事件侦听器对象，以使侦听器能够接收事件通知。
     */
    EventDispatcher.prototype.addEventListener = function(type, listener)
    {
        var map = this._eventMap[type];
        if(map == null) map = this._eventMap[type] = [];
        
        if(map.indexOf(listener) == -1)
        {
            map.push(listener);
            return true;
        }
        return false;
    };

    /**
     * 删除事件侦听器。
     */
    EventDispatcher.prototype.removeEventListener = function(type, listener)
    {
        if(arguments.length == 1) return this.removeEventListenerByType(type);

        var map = this._eventMap[type];
        if(map == null) return false;

        for(var i = 0; i < map.length; i++)
        {
            var li = map[i];
            if(li === listener)
            {
                map.splice(i, 1);
                if(map.length == 0) delete this._eventMap[type];
                return true;
            }
        }
        return false;
    };

    /**
     * 删除指定类型的所有事件侦听器。
     */
    EventDispatcher.prototype.removeEventListenerByType = function(type)
    {
        var map = this._eventMap[type];
        if(map != null)
        {
            delete this._eventMap[type];
            return true;
        }
        return false;
    };

    /**
     * 删除所有事件侦听器。
     */
    EventDispatcher.prototype.removeAllEventListeners = function()
    {   
        this._eventMap = {};
    };

    /**
     * 派发事件，调用事件侦听器。
     */
    EventDispatcher.prototype.dispatchEvent = function(event)
    {
        var map = this._eventMap[event.type];
        if(map == null) return false;   
        if(!event.target) event.target = this;
        map = map.slice();

        for(var i = 0; i < map.length; i++)
        {
            var listener = map[i];
            if(typeof(listener) == "function")
            {
                listener.call(this, event);
            }
        }
        return true;
    };

    /**
     * 检查是否为指定事件类型注册了任何侦听器。
     */
    EventDispatcher.prototype.hasEventListener = function(type)
    {
        var map = this._eventMap[type];
        return map != null && map.length > 0;
    };

    /**
     * 声明一个事件，在严格模式下，如果不声明无法使用，为了避免消息过多无法管理的问题
     */
    EventDispatcher.prototype.defineEvent = function(type, description)
    {
        this._eventDescription[type] = description;
    }

    //添加若干的常用的快捷缩写方法
    EventDispatcher.prototype.on = EventDispatcher.prototype.addEventListener;
    EventDispatcher.prototype.un = EventDispatcher.prototype.removeEventListener;
    EventDispatcher.prototype.fire = EventDispatcher.prototype.dispatchEvent;

    xnote._eventDispatcher = new EventDispatcher();
    xnote.addEventListener = xnote.on = function (type, listener) {
        return xnote._eventDispatcher.addEventListener(type, listener);
    }

    xnote.dispatchEvent = xnote.fire = function (type, target) {
        var event = {type: type, target: target};
        return xnote._eventDispatcher.dispatchEvent(event);
    }
    
})();
