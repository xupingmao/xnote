/**
 * xnote专用ui
 * 依赖库
 *   jquery
 *   layer.js
 * @author xupingmao
 * @since 2017/10/21
 * @modified 2020/01/06 00:07:12
 */
var XUI = function (window) {
  // 处理select标签选中情况
  function initSelect() {  
    $("select").each(function (index, ele) {
      var self = $(ele);
      var children = self.children();
      // 使用$.val() 会取到第一个select标签值
      var value = self.attr("value");
      for (var i = 0; i < children.length; i++) {
        var child = children[i];
        if (value == child.value) {
          child.selected = "selected";
        }
      }
    });
  }

  function initCheckbox() {
    $("input[type=checkbox]").each(function (index, ele) {
      var self = $(ele);
      var value = self.attr("default-value");
      if (value == "on") {
        self.attr("checked", "checked");
      }
    })
  }

  function initRadio() {
    $("input[type=radio]").each(function (index, ele) {
      var self = $(ele);
      var value = self.attr("default-value");
      if (value == self.val()) {
        self.attr("checked", "checked");
      }
    });
  }

  function initXRadio() {
    $(".x-radio").each(function (index, element) {
      var self = $(element);
      var option = self.attr("data-option");
      var value  = self.attr("data-value");
      if (value == option) {
        self.addClass("selected-link");
      }
    });
  }

  // 类似tab的超链接
  function initTabLink() {
    var hasActive = false;
    $(".x-tab").each(function (index, ele) {
      var link = $(ele).attr("href");
      var fullpath = location.href;
      
      if (fullpath.indexOf(link) >= 0) {
        $(ele).addClass("tab-link-active");
        hasActive = true;
      }
    });
    if (!hasActive) {
      $(".x-tab-default").addClass("tab-link-active");
    }
  }
  

  // 点击跳转链接的按钮
  $(".link-btn").click(function () {
      var link = $(this).attr("x-href");
      if (!link) {
        link = $(this).attr("href");
      }
      var confirmMessage = $(this).attr("confirm-message");
      if (confirmMessage) {
        var check = confirm(confirmMessage);
        if (check) {
          window.location.href = link;
        }
      } else {
        window.location.href = link;
      }
  })

  // 点击prompt按钮
  // <input type="button" class="prompt-btn" action="/rename?name=" message="重命名为" value="重命名">
  $(".prompt-btn").click(function () {
      var action = $(this).attr("action");
      var message = $(this).attr("message");
      var defaultValue = $(this).attr("default-value");
      var message = prompt(message, defaultValue);
      if (message != "" && message) {
          $.get(action + encodeURIComponent(message), function () {
              window.location.reload();
          })
      }
  })

  // 点击激活对话框的按钮
  $(".dialog-btn").click(function () {
    var dialogUrl = $(this).attr("dialog-url");
    var dialogId = $(this).attr("dialog-id");
    if (dialogUrl) {
      // 通过新的HTML页面获取dialog
      $.get(dialogUrl, function (respHtml) {
        $(document.body).append(respHtml);
        doModal(dialogId);
        initDefaultValue();
        // 重新绑定事件
        $(".x-dialog-close, .x-dialog-cancel").unbind("click");
        $(".x-dialog-close, .x-dialog-cancel").on("click", function () { onDialogHide(); });
      })
    }
  });

  /**
   * 初始化弹层
   */
  function initDialog() {
    // 初始化样式
    $(".x-dialog-close").css({"background-color":"red", "float":"right"});

    $(".x-dialog").each(function (index, ele) {
        var self = $(ele);
        var width = window.innerWidth;
        if (width < 600) {
          dialogWidth = width - 40;
        } else {
          dialogWidth = 600;
        }
        var top = Math.max((getWindowHeight() - self.height()) / 2, 0);
        var left = (width - dialogWidth) / 2;
        self.css({"width":dialogWidth, "left": left}).css("top", top);
    });

    $("body").css("overflow", "hidden");
  }
  
  /**
   * 隐藏弹层
   */
  function onDialogHide() {
      $(".x-dialog").hide();
      $(".x-dialog-background").hide();
      $(".x-dialog-remote").remove();// 清空远程的dialog
      $("body").css("overflow", "auto");
  }
  
  $(".x-dialog-background").click(function () {
      onDialogHide();
  });
  
  $(".x-dialog-close, .x-dialog-cancel").click(function () {
      onDialogHide();
  });
  
  function doModal(id) {
    initDialog();
    $(".x-dialog-background").show();
    $(".x-dialog-remote").show();
    $("#"+id).show();
  }

  // 初始化表单控件的默认值
  function initDefaultValue() {
    initSelect();
    initCheckbox();
    initRadio();
    initXRadio();
    initTabLink();
  }

  window.showToast = function (message, time) {
    if (!time) {
      time = 1000;
    }
    var maxWidth = $(document.body).width();
    var fontSize = 14;
    var toast = $("<div>").css({
      "margin": "0 auto",
      "position": "fixed",
      "left": 0,
      "top": "24px",
      "font-size": fontSize,
      "padding": "14px 18px",
      "border-radius": "4px",
      "background": "#000",
      "opacity": 0.7,
      "color": "#fff",
      "line-height": "22px",
      "z-index": 1000
    });
    toast.text(message);

    $(document.body).append(toast);
    var width = toast.outerWidth();
    var left = (maxWidth - width) / 2;
    if (left < 0) {
      left = 0;
    }
    toast.css("left", left);
    setTimeout(function () {
      toast.remove();
    }, time);
  }

  // Dropdown 控件
  $(".dropdown").click(function (e) {
      var target = e.target;
      $(target).next(".dropdown-content").slideToggle("fast");
  });

  $("body").on("click", function (e) {
      var target = e.target;
      if ($(target).hasClass("dropdown") || $(target).hasClass("dropdown-btn")) {
          return;
      }
      $(".dropdown-content").hide();
  });

  // 初始化
  initDefaultValue();
};

$(document).ready(function () {
    XUI(window);
})

