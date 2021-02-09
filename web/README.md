# web端

**注意：源代码中包含Google Analytics分析代码，`index.html`, `search.html`和`resource.html`**

# requirements

* tornado
* mongodb
* pymongo
* cryptography

# 导入数据

**注意：不兼容channel中分享的MongoDB数据**
暂时没有开箱即用的数据，一个workaround如下：

1. 下载[MySQL的数据](https://t.me/mikuri520/668)
1. 导入数据到MySQL
2. 运行 `python prepare/convert_db.py`

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
