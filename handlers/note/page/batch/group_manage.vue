<!-- vue和layer弹层组件协作不太顺利，单独使用art-template模板引擎了，后面可以使用vue的弹层组件 -->
<div id="vueApp">
    <div class="card btn-line-height">
        <div class="row">
            <span>标签</span>
            <a href="?" class="tag lightgray large {% if len(q_tags) == 0 %}active{%end%}">全部</a>
            <a v-for="tag in tagList" @click="onTagClick(tag)"
                class="test tag lightgray meta" 
                v-bind:class="{'active': filterTags.indexOf(tag.tag_name)>=0 }">{{! tag.tag_name }}</a>
        </div>

        <div class="row top-offset-1">
            <button class="create-tag-btn btn-default">创建新标签</button>
            <button class="delete-tag-btn btn danger">删除标签</button>
        </div>
    </div>

    <div class="hide bind-tag-dialog" ref="bindTagDialog">
        <div class="card btn-line-height">
            <a v-for="tag in tagList" class="tag lightgray for-dialog large" 
                v-bind:class="{'active': selectedNames[tag.tag_name] }">
                <span class="tag-id hide">{{! tag._id }}</span>
                <span class="tag-name">{{! tag.tag_name }}</span>
            </a>
        </div>
    </div>
</div>

<script type="text/javascript" src="/static/lib/vue/vue-2.2.6.min.js"></script>
<script>
(function () {
    var app = new Vue({
        el: "#vueApp",
        data: {
            key: 1,
            tagList: [],
            filterTags: [],
            selectedIds: {},
            selectedNames: {},
        },
        methods: {
            reloadTagList: function () {
                var self = this;
                self.filterTags = JSON.parse(xnote.getUrlParam("tags", "[]"));
                console.log(self.filterTags);

                $.get("/note/tag/list?tag_type=book", function (resp) {
                    console.log("resp", resp);
                    if (resp.code != "success") {
                        xnote.alert(resp.message);
                    } else {
                        self.tagList = resp.data;
                    }
                });
            },
            onTagClick: function (tag) {

            },
            update: function() {
                this.$forceUpdate();
            },
        }
    });

    window.debugApp = app;

    app.reloadTagList();

})();
</script>
