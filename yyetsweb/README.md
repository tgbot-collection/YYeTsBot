# web端

**注意：源代码中包含Google Analytics分析代码，`index.html`, `search.html`和`resource.html`。如果自己使用，要记得去除哦**

# requirements

* tornado
* mongodb
* pymongo

# 导入数据

从 [这里](https://yyets.dmesg.app/database) 下载mongodb数据，然后导入

```shell
mongorestore --gzip --archive=yyets_mongo.gz --nsFrom "share.*" --nsTo "zimuzu.*"
```

# 运行

`python server.py`

# Docker

参考[这里](https://github.com/BennyThink/WebsiteRunner)

# MongoDB index

```shell
use zimuzu;

db.getCollection('yyets').createIndex({"data.info.id": 1});
db.getCollection('yyets').createIndex({"data.info.views" : -1});
db.getCollection('yyets').createIndex({"data.info.area" : 1});
db.getCollection('yyets').getIndexes();

db.getCollection('douban').createIndex({"resourceId" : 1});
db.getCollection('douban').getIndexes();

db.getCollection('users').createIndex({"username" : 1}, { unique: true });
db.getCollection('users').createIndex(
   { "email.address": 1 },
   { unique: true, partialFilterExpression: { "email.address": { $exists: true } } }
)
db.getCollection('users').getIndexes();

db.getCollection('comment').createIndex({"resource_id" : 1});
db.getCollection('comment').getIndexes();

db.getCollection('reactions').createIndex({"comment_id" : 1});
db.getCollection('reactions').getIndexes();

db.getCollection('metrics').createIndex({"date" : 1});
db.getCollection('metrics').getIndexes();

db.getCollection('notification').createIndex({"username" : 1});
db.getCollection('notification').getIndexes();

```
