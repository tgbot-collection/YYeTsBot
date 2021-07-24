# web端

**注意：源代码中包含Google Analytics分析代码，`index.html`, `search.html`和`resource.html`。如果自己使用，要记得去除哦**

# requirements

* tornado
* mongodb
* pymongo

# 导入数据

从 [这里](https://yyets.dmesg.app/database) 下载mongodb数据，然后导入

```shell
mongorestore --gzip --archive=yyets_mongo.gz
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
```
