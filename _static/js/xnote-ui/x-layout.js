
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
    var offset = this.offset();
    if (offset === undefined) {
        return;
    }
    var topDiff = offset.top - parent.offset().top + offsetY;
    parent.scrollTop(topDiff);
};



// 计算文本的高度
xnote.layout.getTextareaTextHeight = function(textarea) {
    // 将原生元素转换为 jQuery 对象
    var $textarea = $(textarea);
    
    // 创建一个克隆元素来计算文本高度
    var $clone = $('<div />')
        .css({
            position: 'absolute',
            top: '-9999px',
            left: '-9999px',
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            boxSizing: $textarea.css('box-sizing')
        })
        .width($textarea.outerWidth())
        .appendTo('body');
    
    // 复制相关样式到克隆元素
    var props = [
        'fontFamily', 'fontSize', 'fontWeight', 'fontStyle',
        'letterSpacing', 'textTransform', 'wordSpacing', 'textIndent',
        'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
        'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
        'lineHeight'
    ];
    
    for (var i = 0; i < props.length; i++ ) {
        var prop = props[i];
        $clone.css(prop, $textarea.css(prop));
    }
    
    // 设置内容，优先使用 value，否则使用 placeholder
    $clone.text($textarea.val() || $textarea.attr('placeholder') || '');
    
    // 获取内容高度
    var height = $clone.outerHeight();
    
    // 移除克隆元素
    $clone.remove();
    
    return height;
}    