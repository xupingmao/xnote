
# build css files
echo > ./static/css/app.build.css
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
cat ./static/js/xnote-ui.js >> ./static/js/app.build.js
cat ./static/js/app.js >> ./static/js/app.build.js
cat ./static/js/layer.photos.js >> ./static/js/app.build.js
