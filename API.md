# 资源

## 获取指定id的资源

* GET `/api/resource?id=10004`
  数据结构参考 [sample.json](yyetsweb/js/sample.json)

## 搜索

* GET `/api/resource?keyword=逃避`

```json
{
  "data": [
    {
      "data": {
        "info": {
          "id": 34812,
          "cnname": "逃避可耻却有用",
          "enname": "NIGERUHA HAJIDAGA YAKUNITATSU",
          "aliasname": "逃避虽可耻但有用 / 雇佣妻子(港) / 月薪娇妻(台) / 逃跑是可耻但是有用 / 逃避虽可耻但很有用 / 逃避可耻但有用",
          "channel": "tv",
          "channel_cn": "日剧",
          "area": "日本",
          "show_type": "",
          "expire": "1610399344",
          "views": 1201,
          "year": [
            2016,
            2017,
            2021
          ]
        }
      }
    },
    {
      "data": {
        "info": {
          "id": 29540,
          "cnname": "无法逃避",
          "enname": "Inescapable",
          "aliasname": "无法避免",
          "channel": "movie",
          "channel_cn": "电影",
          "area": "加拿大",
          "show_type": "",
          "expire": "1610396227",
          "views": 1,
          "year": [
            2012
          ]
        }
      }
    },
    {
      "data": {
        "info": {
          "id": 37089,
          "cnname": "逃避者",
          "enname": "Shirkers",
          "aliasname": "",
          "channel": "movie",
          "channel_cn": "电影",
          "area": "美国",
          "show_type": "",
          "expire": "1610400512",
          "views": 0,
          "year": [
            2018
          ]
        }
      }
    }
  ]
}
```

# Top

获取top信息，每类返回15条访问量最高的数据

* GET `/api/top`

```json
{
  "ALL": [
    {
      "data": {
        "info": {
          "id": 39894,
          "cnname": "速度与激情9",
          "enname": "F9: The Fast Saga",
          "aliasname": "F9狂野时速(港)/玩命关头9(台)/狂野时速9/速激9/FF9/Fast & Furious 9",
          "channel": "movie",
          "channel_cn": "电影",
          "area": "美国",
          "show_type": "",
          "expire": "1610401946",
          "views": 47466,
          "year": [
            2021
          ]
        }
      }
    },
    {
      "data": {
        "info": {
          "id": 38413,
          "cnname": "致命女人",
          "enname": "Why Women Kill",
          "aliasname": "女人为什么杀人/女人为何杀戮",
          "channel": "tv",
          "channel_cn": "美剧",
          "area": "美国",
          "show_type": "",
          "expire": "1610401185",
          "views": 39040,
          "year": [
            2019
          ]
        }
      }
    }
  ],
  "US": [],
  "JP": [],
  "KR": [],
  "UK": [],
  "class": {
    "ALL": "全部",
    "US": "美国",
    "JP": "日本",
    "KR": "韩国",
    "UK": "英国"
  }
}
```

# 个人中心

获取个人收藏

* GET /api/like

```json
{
  "LIKE": [
    {
      "data": {
        "info": {
          "id": 39523,
          "cnname": "禁忌女孩",
          "enname": "เด็กใหม่",
          "aliasname": "来路不明的转校生/Girl from Nowhere",
          "channel": "tv",
          "channel_cn": "泰剧",
          "area": "泰国",
          "show_type": "",
          "expire": "1610401752",
          "views": 979,
          "year": [
            2020
          ]
        }
      }
    }
  ]
}
```

# 用户

## 登录或注册

* POST `/api/user`，提交json，字段 `username`, `password`

## 获取当前登录用户信息

登录用户可用，未登录会返回401

* GET `/api/user`

```json
{
  "username": "Benny",
  "date": "2021-03-12 11:11:11",
  "last_date": "2021-03-15 13:11:18",
  "ip": "1.1.1.1",
  "last_ip": "2.2.2.2",
  "browser": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.85 Safari/537.36",
  "like": [
    11133
  ],
  "group": [
    "admin",
    "user"
  ]
}
```

# 获取全部剧集名称

* GET `/api/name`
* GET `/api/name?human=1` 人类可读

# 添加或删除收藏

* PATCH `/api/user`，提交json，字段 `resource_id`

# 评论

## 获取评论

* GET `/api/comment`

分页，支持URL参数：

* resource_id: 资源id，id为233是留言板，id为-1会返回最新评论
* size: 每页评论数量，默认5（或者其他数值）
* page: 当前页

返回

```json
{
  "data": [
    {
      "date": "2018-09-18 11:12:15",
      "username": "uuua2",
      "content": "tdaadd",
      "id": 2
    },
    {
      "date": "2018-09-01 11:12:15",
      "username": "abcd",
      "content": "tdaadd",
      "id": 1
    }
  ],
  "count": 2,
  "resource_id": 39301
}

```

## 获取验证码

* GET `/api/captcha?id=1234abc`，id是随机生成的字符串 API 返回字符串，形如 `data:image/png;base64,iVBORw0KGgoAAA....`

## 提交评论

* POST `/api/comment`
  只有登录用户才可以发表评论，检查cookie `username` 是否为空来判断是否为登录用户；未登录用户提示“请登录后发表评论”

`resource_id` 从URL中获取，id是上一步验证码的那个随机字符串id， `captcha` 是用户输入的验证码

```json
{
  "resource_id": 39301,
  "content": "评论内容",
  "id": "1234abc",
  "captcha": "38op"
}
```

返回 HTTP 201添加评论成功，403/401遵循HTTP语义

```json
{
  "message": "评论成功/评论失败/etc"
}
```

# metrics

## 添加metrics

* POST `/api/metrics`, json,字段 `type`

## 获取metrics

* GET `/api/metrics`，默认返回最近7天数据，可选URL参数 `from`, `to`，如 `from=2021-03-12&to=2021-03=18

# Grafana

* GET `/api/grafana/`
* GET `/api/grafana/search`
* GET `/api/grafana/query`

# 黑名单

* GET `/api/blacklist`

# 获取备份数据库信息

* GET `/api/db_dump`

```json
{
  "yyets_mongo.gz": {
    "checksum": "b32e9d8e24c607a9f29889a926c15179d9179791",
    "date": "2021-06-14 12:59:51",
    "size": "6.0B"
  },
  "yyets_mysql.zip": {
    "checksum": "6b24ae7cb7cef42951f7e2df183f0825512029e0",
    "date": "2021-06-14 12:59:51",
    "size": "11.0B"
  },
  "yyets_sqlite.zip": {
    "checksum": "7e1659ab5cbc98b21155c3debce3015c39f1ec05",
    "date": "2021-06-14 12:59:51",
    "size": "15.0B"
  }
}
```

# 公告

## 添加公告

* POST `/api/announcement`, json 字段 content

## 获取公告

* GET `/api/announcmement`，接受URL参数 size、page

```json
{
  "data": [
    {
      "username": "Benny",
      "date": "2021-06-15 16:28:16",
      "browser": "PostmanRuntime/7.28.0",
      "content": "hello"
    }
  ],
  "count": 1
}
```
