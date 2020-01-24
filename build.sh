
# build css files
echo > ./static/css/app.build.css
cat ./static/css/reset.css >> ./static/css/app.build.css
cat ./static/lib/font-awesome-4.7.0/css/font-awesome.min.css >> ./static/css/app.build.css
cat ./static/css/common.css >> ./static/css/app.build.css
cat ./static/css/app.css >> ./static/css/app.build.css
cat ./static/css/message.css >> ./static/css/app.build.css
cat ./static/css/note.css >> ./static/css/app.build.css
cat ./static/css/plugins.css >> ./static/css/app.build.css

# build js files
echo > ./static/js/app.build.js
# layer需要加载css资源
# cat ./static/lib/jquery/jquery-1.12.4.min.js >> ./static/js/app.build.js
# cat ./static/lib/layer/layer.js >> ./static/js/app.build.js
cat ./static/js/utils.js >> ./static/js/app.build.js

# xnote-ui
cat ./static/js/xnote-ui/EventDispatcher.js >> ./static/js/app.build.js
cat ./static/js/xnote-ui/core.js >> ./static/js/app.build.js
cat ./static/js/xnote-ui/layer.photos.js >> ./static/js/app.build.js
cat ./static/js/xnote-ui/x-device.js >> ./static/js/app.build.js
cat ./static/js/xnote-ui/x-dropdown.js >> ./static/js/app.build.js
cat ./static/js/xnote-ui/x-photo.js >> ./static/js/app.build.js
cat ./static/js/xnote-ui/x-audio.js >> ./static/js/app.build.js
cat ./static/js/xnote-ui/x-upload.js >> ./static/js/app.build.js
cat ./static/js/xnote-ui/x-dialog.js >> ./static/js/app.build.js

# app 
cat ./static/js/app.js >> ./static/js/app.build.js
