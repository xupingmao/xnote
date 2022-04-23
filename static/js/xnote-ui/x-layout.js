
// 根据内容自动调整高度
$.fn.autoHeight = function(){    
    function autoHeight(elem){
        elem.style.height = 'auto';
        elem.scrollTop = 0; //防抖动
        elem.style.height = elem.scrollHeight + 'px';
    };

    this.each(function(){
        autoHeight(this);
        $(this).on('keyup', function(){
            autoHeight(this);
        });
    });
};

// 在滚动条中展示
$.fn.showInScroll = function(offsetY) {
    if (offsetY === undefined) {
        offsetY = 0;
    }

    var parent = this.parent();
    var topDiff = this.offset().top - parent.offset().top + offsetY;
    parent.scrollTop(topDiff);
};

