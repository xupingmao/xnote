var menu = [
    {id: "", text:"功能集合", cl:"nav-header", title:"主页"},
    {id: "fs", text:"文件系统", href:"/fs?menu=fs"},
    {id: "db", text:"数据库", href:"/db?menu=db"},
    {id: "doc", text:"文档", href:"/simple?menu=doc&url=doc/main.html"},
    {id: "cam", text: "摄像头", href:"/simple?menu=cam&url=cam/main.html"},
    {id: "colorpicker", text:"颜色选择器", href:"/simple?menu=colorpicker&url=colorpicker/main.html"},
    {id: "img", text:"图片浏览器", href:"/simple?menu=img&url=img/main.html"},
    {id: "console", text:"控制台", href:"/simple?menu=console&url=console/main.html"},
    {id: "blog", text:"博客", href: "/simple?menu=blog&url=blog/main.html"},
    {id: "note", text:"笔记", href: "/simple?menu=note&url=note/main.html"}
];

function setTitle(id) {
    for(var i = 0; i < menu.length; i++) {
        if (menu[i].id == id) {
            if (menu[i].title) {
                $("#title").text(menu[i].title);
            } else {
                $("#title").text(menu[i].text)
            }
            break;
        }
    }
}