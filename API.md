# 需求与待开发功能

## FE

- [x] group为admin特殊显示，评论接口已返回group信息
- [x] 评论楼中楼
- [x] 联合搜索，当本地数据库搜索不到数据时，会返回extra字段
- [x] 最新评论
- [x] 公告
- [ ] 分类
- [ ] 最新更新资源
- [ ] 评论通知（浏览器通知）
- [ ] API变更：登录时需要验证码
- [ ] API变更：like API变更 PATCH `/api/user/` --> PATCH `/api/like/`
- [ ] 删除评论（admin only）

# BE

- [x] 联合搜索：字幕侠、new字幕组、追新番
- [x] grafana面板
- [x] 豆瓣接口
- [x] 评论通知：站内通知
- [x] 添加邮箱
- [x] 邮件通知
- [ ] 找回密码
- [ ] 添加资源

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

当数据库搜索不到资源时，会尝试从字幕侠、new字幕组和追新番搜索，返回如下

```json
{
  "data": [],
  "extra": [
    {
      "url": "https://www.zimuxia.cn/portfolio/%e4%b8%9c%e5%9f%8e%e6%a2%a6%e9%ad%87",
      "name": "东城梦魇",
      "class": "ZimuxiaOnline"
    },
    {
      "url": "https://www.zimuxia.cn/portfolio/%e9%bb%91%e8%89%b2%e6%ad%a2%e8%a1%80%e9%92%b3",
      "name": "黑色止血钳",
      "class": "ZimuxiaOnline"
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

* GET `/api/like`

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

返回json

## 获取当前登录用户信息

登录用户可用，未登录会返回401

* GET `/api/user`

```json
{
  "username": "Benny",
  "date": "2021-06-12 13:55:50",
  "ip": "172.70.122.84",
  "browser": "Mozilla/5.0 (X11; Gentoo; rv:84.0) Gecko/20100101 Firefox/84.0",
  "like": [
    31346,
    39894,
    41382
  ],
  "group": [
    "admin"
  ],
  "comments_like": [
    "60c46d6a6d7c5dd22d69fd3b"
  ],
  "comments_dislike": [
    "60c46d6a6d7c5dd22d69fd3b"
  ],
  "email": {
    "verified": false,
    "address": "123@qq.com"
  }
}
```

## 更改用户信息

* PATCH `http://127.0.0.1:8888/api/user`

* 目前只支持修改email字段，会发送验证邮件，1800秒之内只能验证一次，有效期24小时

暂不支持取消绑定

```json
{
  "email": "123@qq.com"
}
```

response

```json
{
  "status_code": 429,
  "status": false,
  "message": "try again in 1797s"
}
```

## 验证邮件

* POST `http://127.0.0.1:8888/api/user/email`

10次错误会被加到黑名单，账号注销

```json
{
  "code": "83216"
}
```

response

```json
{
  "status": true,
  "status_code": 201,
  "message": "success"
}
```

# 获取全部剧集名称

* GET `/api/name`
* GET `/api/name?human=1` 人类可读

# 添加或删除收藏

* PATCH `/api/like`，提交json，字段 `resource_id`

# 评论

评论的基本数据格式： `children` 字段为 array/list，可套娃另外一条评论，目前暂时只支持两层（也不打算支持更多的啦）。

评论的 `resource_id` 必须相同

## 普通评论

```json
{
  "username": "Benny",
  "date": "2021-06-17 10:54:19",
  "browser": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.13; rv:85.1) Gecko/20100101 Firefox/85.1",
  "content": "test",
  "resource_id": 233,
  "id": "60cab95baa7f515ea291392b",
  "children": [
  ],
  "childrenCount": 0
}

```

## 嵌套评论

```json
{
  "username": "Benny",
  "date": "2021-06-17 10:54:19",
  "browser": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.13; rv:85.1) Gecko/20100101 Firefox/85.1",
  "content": "test",
  "resource_id": 233,
  "id": "60cab95baa7f515ea291392b",
  "children": [
    {
      "username": "Alex",
      "date": "2021-05-31 16:58:21",
      "browser": "PostmanRuntime/7.28.0",
      "content": "评论17",
      "id": "60c838a12a5620b7e4ba5dfc",
      "resource_id": 233
    },
    {
      "username": "Paul",
      "date": "2021-05-22 16:58:21",
      "browser": "PostmanRuntime/7.28.0",
      "content": "评论14",
      "id": "60c838a12a5620b7e4ba1111",
      "resource_id": 233
    }
  ],
  "childrenCount": 2
}

```

## 获取评论

* GET `/api/comment`

分页，支持URL参数：

* resource_id: 资源id，id为233是留言板，id为-1会返回最新评论
* size: 每页评论数量，默认5
* page: 当前页，默认1
* inner_size: 内嵌评论数量，默认5
* inner_page: 内嵌评论当前页，默认1
  **注意：如上两个inner参数是对整个页面生效的，如要进行某个父评论的子评论分页，请参考下面的子评论分页接口 返回 楼中楼评论，group表示用户所属组，admin是管理员，user是普通用户

```json
{
  "data": [
    {
      "username": "Benny",
      "date": "2021-06-22 18:26:42",
      "browser": "PostmanRuntime/7.28.0",
      "content": "父评论benny",
      "resource_id": 233,
      "type": "parent",
      "id": "60d1bae2d87ce6e9a2934a0f",
      "group": [
        "admin"
      ]
    },
    {
      "username": "Benny",
      "date": "2021-06-22 18:24:44",
      "browser": "PostmanRuntime/7.28.0",
      "content": "父评论benny",
      "resource_id": 233,
      "type": "parent",
      "group": [
        "admin"
      ],
      "childrenCount": 22,
      "children": [
        {
          "username": "test",
          "date": "2021-06-22 18:25:12",
          "browser": "PostmanRuntime/7.28.0",
          "content": "admin子评2论2",
          "resource_id": 233,
          "type": "child",
          "id": "60d1ba88d87ce6e9a2934a0c",
          "group": [
            "user"
          ]
        },
        {
          "username": "admin",
          "date": "2021-06-22 18:25:08",
          "browser": "PostmanRuntime/7.28.0",
          "content": "admin子评论2",
          "resource_id": 233,
          "type": "child",
          "id": "60d1ba84d87ce6e9a2934a0a",
          "group": [
            "user"
          ]
        }
      ],
      "id": "60d1ba6cd87ce6e9a2934a08"
    }
  ],
  "count": 2,
  "resource_id": 233
}
```

## 子评论分页

* GET `/api/comment/child`
  URL参数：
* parent_id:父评论id
* size: 每页评论数量，默认5
* page: 当前页，默认1

`/api/comment/child?parent_id=60dfc932802d2c69cf8774ce&size=2&page=2`

返回子评论

```json
{
  "data": [
    {
      "username": "Benny",
      "date": "2021-07-03 10:22:13",
      "browser": "PostmanRuntime/7.28.1",
      "content": "子15",
      "resource_id": 233,
      "type": "child",
      "id": "60dfc9d5802d2c69cf877514",
      "childrenCount": 17,
      "group": [
        "admin"
      ]
    },
    {
      "username": "Benny",
      "date": "2021-07-03 10:22:11",
      "browser": "PostmanRuntime/7.28.1",
      "content": "子14",
      "resource_id": 233,
      "type": "child",
      "id": "60dfc9d3802d2c69cf877512",
      "group": [
        "admin"
      ]
    }
  ],
  "count": 17
}
```

## 获取验证码

* GET `/api/captcha?id=1234abc`，id是随机生成的字符串 API 返回字符串，形如 `data:image/png;base64,iVBORw0KGgoAAA....`

## 提交评论

* POST `/api/comment`
  只有登录用户才可以发表评论，检查cookie `username` 是否为空来判断是否为登录用户；未登录用户提示“请登录后发表评论”

`resource_id` 从URL中获取，id是上一步验证码的那个随机字符串id， `captcha` 是用户输入的验证码

### 提交新评论

只需要提供如下四项信息即可

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

### 提交楼中楼评论

还需要额外提供一个 `comment_id`，也就是 UUID，如 `60c838a12a5620b7e4ba5dfc`

```json
{
  "resource_id": 39301,
  "content": "评论内容",
  "id": "1234abc",
  "captcha": "38op",
  "comment_id": "60c838a12a5620b7e4ba5dfc"
}
```

## 删除评论，软删除

* DELETE `/api/comment`，提交json数据

```json
{
  "comment_id": "60cab935e9f929e09c91392a"
}
```  

不用关心comment_id是子评论还是父评论，会自动删除

返回被删除的数量,HTTP 200表示删除成功，404表示未找到这条留言

```json
{
  "status_code": 404,
  "message": "",
  "count": 0
}
```

## 最新评论

* GET `api/comment/newest`
  page size参数同上

```json
{
  "data": [
    {
      "username": "111",
      "date": "2021-07-11 10:22:59",
      "browser": "Mozi0.31.0",
      "content": "1111？",
      "resource_id": 233,
      "type": "parent",
      "id": "60ea53113178773",
      "group": [
        "user"
      ],
      "cnname": "留言板"
    },
    {
      "username": "11111222",
      "date": "2021-07-10 23:54:43",
      "browser": "Mozi3322.64",
      "content": "<reply value=\"60e939be4ad7f20773865d7a\">@abcd</reply>怎么下载啊\n",
      "resource_id": 37552,
      "type": "child",
      "id": "60e9c2c222111397e",
      "group": [
        "user"
      ],
      "cnname": "黑寡妇"
    },
    {
      "username": "1111",
      "date": "2021-07-10 23:41:06",
      "browser": "Moz) Chrom.864.67",
      "content": "我是1精彩",
      "resource_id": 41382,
      "type": "parent",
      "id": "60e9bf924ad7f2077381111",
      "group": [
        "user"
      ],
      "cnname": "洛基"
    }
  ],
  "count": 294
}
```

## 点赞或踩评论

* PATCH `/api/comment`

verb 为`like` 或 `dislike`

```json
{
  "comment_id": "60c46d6a6d7c5dd22d69fd3b",
  "verb": "dislike/like"
}

```

返回：

* 201 成功
* 404 评论没找到
* 422 已经赞/踩过了
* 400 请求参数错误

用户曾经点赞的记录会在 `GET /api/user` 返回

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

* GET `/api/announcement`，接受URL参数 size、page

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

# 豆瓣

## 获取简介等信息

* GET `/api/douban?resource_id=34812`
  第一次请求会比较慢

```json
{
  "name": "逃避可耻却有用",
  "doubanId": 26816519,
  "doubanLink": "https://movie.douban.com/subject/26816519/",
  "posterLink": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2400201631.jpg",
  "resourceId": 34812,
  "rating": "8.4",
  "actors": [
    "新垣结衣",
    "星野源",
    "大谷亮平",
    "藤井隆",
    "真野惠里菜",
    "成田凌",
    "山贺琴子",
    "宇梶刚士",
    "富田靖子",
    "古田新太",
    "石田百合子",
    "细田善彦",
    "古馆宽治",
    "叶山奖之"
  ],
  "directors": [
    "金子文纪",
    "土井裕泰",
    "石井康晴"
  ],
  "genre": [
    "喜剧"
  ],
  "releaseDate": "2016-10-11(日本)",
  "episodeCount": " 11",
  "episodeDuration": " 45分钟",
  "writers": [
    "野木亚纪子",
    "海野纲弥"
  ],
  "year": "2016",
  "introduction": "森山实栗（新垣结衣饰）自研究生毕业之后就一直仕途不顺，最近更是惨遭解雇，处于“无业游民”的状态之下，日子过得十分凄惨。经由父亲的介绍，无处可去的实栗来到了名为津崎平匡（星野源饰）的单身男子家中，为其料理家事，就这样，二十五岁的实栗成为了一名家政妇。实栗心地善良手脚勤快，在她的安排和劳作下，平匡家中的一切被打理的井井有条，实栗因此获得了平匡的信赖，亦找到了生活的重心，重新振作了起来。然而好景不长，实栗的父母决定搬离此地，这也就意味着实栗必须“离职”。实在无法接受此事的实栗决定和平匡“契约结婚”，在外装做夫妻，在内依旧是雇主和职员。就这样，这对“孤男寡女”开始了他们的同居生活。"
}
```

## 获取海报

* GET `api/douban?resource_id=34812&type=image`
  会返回相应格式（jpeg、webp、png等）的图片，与上次数据中 `posterLink`所看到的内容相同

# 验证码

## 获取验证码

* GET `/api/captcha?id=1234abc`，id是随机生成的字符串 API 返回字符串，形如 `data:image/png;base64,iVBORw0KGgoAAA....`

## 校验验证码

除去评论中的校验验证码，如有额外需求，也可以使用 POST 方法校验

* POST `/api/captcha`

```json
{
  "id": "1234abc",
  "captcha": "38op"
}
```

# 豆瓣报错

## 提交

* POST `/api/douban/report`

```json
{
  "captcha_id": "用户输入的验证码",
  "id": "验证码id",
  "content": "内容难过-咔咔",
  "resource_id": 23133312
}
```

## 查询

* GET `/api/douban/report`

```json
{
  "data": [
    {
      "resource_id": 2333,
      "content": [
        "dddd",
        "1款大家咔咔",
        "1款大家dadadada-咔咔"
      ]
    },
    {
      "resource_id": 23133,
      "content": [
        "1款大家dadadada-咔咔"
      ]
    },
    {
      "resource_id": 23133312,
      "content": [
        "1款大家dadadada-咔咔"
      ]
    }
  ]
}
```

# 通知

只有登录用户可以获取，只有楼主能够获取到通知，其他楼层的人获取不到。

## 获取通知

* GET `http://127.0.0.1:8888/api/notification`

支持URL参数page和size，默认1和5

```json
{
  "_id": "61013c0f89c9cd0c75460184",
  "username": "user1",
  "unread_item": [
    {
      "_id": "61013c839633a80254ef2e38",
      "username": "user3",
      "date": "2021-07-28 19:16:19",
      "browser": "Mozilla/5.0 (Windows NT 6.3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.123 Safari/537.36",
      "content": "<reply value=\"61013c0f9633a80254ef2e30\">@user2</reply>user3",
      "resource_id": 233,
      "type": "child"
    }
  ],
  "read_item": [
    {
      "_id": "61013c0f9633a80254ef2e30",
      "username": "user2",
      "date": "2021-07-28 19:14:23",
      "browser": "Mozilla/5.0 (X11; Gentoo; rv:82.0) Gecko/20100101 Firefox/82.0",
      "content": "<reply value=\"610135c9d1f873388feb5c78\">@user1</reply>okkk",
      "resource_id": 233,
      "type": "child"
    }
  ]
}
```

# 已读、未读消息

* PATCH `http://127.0.0.1:8888/api/notification`
  json body

```json
{
  "comment_id": "61013c839633a80254ef2e38",
  "verb": "unread"
}
```

verb只可以是 `read` 和 `unread`
comment_id 是评论的id

# 分类

最灵活的API！ 推荐组合方式： 国家、分类

* GET `/api/category`

参数 `douban=True` 会返回豆瓣信息，默认不返回 支持如下参数，均为可选参数，可自由组合，URL参数可以URL编码，也可以不编码：

## 分页参数

* page 默认1
* size 默认15

## channel

大分类，电影、电视剧、公开课，详细分类可以使用 `channel_cn`

```python
[('movie', 12057), ('tv', 5428), ('openclass', 35), ('discuss', 1)]
```

## channel_cn

推荐值：

```python
[('电影', 12057), ('美剧', 2119), ('日剧', 1215), ('英剧', 641), ('纪录片', 314), ('韩剧', 212), ('动画', 126), ('泰剧', 112),
 ('加剧', 82), ('西剧', 62), ('澳剧', 61)]

```

全部可选值：

```python
[('电影', 12057), ('美剧', 2119), ('日剧', 1215), ('英剧', 641), ('纪录片', 314), ('韩剧', 212), ('动画', 126), ('泰剧', 112),
 ('加剧', 82), ('西剧', 62), ('澳剧', 61), ('真人秀', 51), ('法剧', 50), ('德剧', 41), ('公开课', 35), ('其剧', 34), ('越剧', 23),
 ('巴剧', 21), ('俄剧', 21), ('意剧', 19), ('墨剧', 16), ('印剧', 16), ('土剧', 16), ('\x00剧', 12), ('电视电影', 12), ('脱口秀', 10),
 ('挪威剧', 9), ('丹麦剧', 8), ('综艺', 7), ('葡萄牙剧', 6), ('颁奖礼', 5), ('以色列剧', 4), ('新剧', 4), ('菲律宾剧', 4), ('动漫', 4), ('瑞典剧', 4),
 ('新西兰剧', 4), ('神剧', 3), ('短视频', 3), ('舞台剧', 3), ('MV', 3), ('演讲', 3), ('颁奖典礼', 3), ('比利时剧', 3), ('南非剧', 3), ('电视剧', 3),
 ('晨间剧', 2), ('短片', 2), ('荷兰剧', 2), ('巴西电视剧', 2), ('爱尔兰剧', 2), ('汽车三贱客', 2), ('芬兰剧', 2), ('大剧', 2), ('美剧 律政', 1),
 ('美剧/英剧', 1), ('小镇疑云(美版)', 1), ('动画片', 1), ('埃剧', 1), ('探案', 1), ('纪录', 1), ('演唱会', 1), ('冰岛剧', 1), ('深夜剧', 1),
 ('萌剧', 1), ('律政/剧情', 1), ('2013年BBC历史记录片', 1), ('催眠剧', 1), ('波兰剧', 1), ('幼教', 1), ('约旦', 1), ('闹剧', 1), ('浪漫/喜剧', 1),
 ('悬疑/罪案', 1), ('BBC世界杯专题纪录片', 1), ('克罗地亚剧', 1), ('台剧', 1), ('墨西哥剧', 1), ('惊悚', 1), ('阿拉伯剧', 1), ('委内瑞拉电视剧', 1),
 ('音乐会', 1), ('巴西剧', 1), ('新闻', 1), ('土耳其剧', 1), ('约旦剧', 1), ('发布会', 1), ('丹麦瑞典合拍', 1), ('捷克剧', 1), ('越南剧', 1),
 ('剧情', 1), ('墨西哥电视剧', 1), ('韩综', 1), ('花絮', 1), ('', 1)]

```

## area

**推荐使用**
推荐值

```python
[('美国', 9057), ('日本', 2233), ('英国', 1637), ('法国', 902), ('韩国', 763), ('其他', 535), ('德国', 402), ('加拿大', 313),
 ('西班牙', 280), ('印度', 247), ('俄罗斯', 234), ('泰国', 191), ('澳大利亚', 182), ('意大利', 150), ('', 109), ('越南', 60), ('巴西', 54),
 ('大陆', 52), ('墨西哥', 40), ('土耳其', 35), ('新加坡', 23), ('香港', 20), ('埃及', 1), ('台湾', 1)]

```

## show_type

不推荐使用！数据缺失非常严重

```python
[('', 16751), ('纪录片', 314), ('动画', 126), ('日剧', 110), ('真人秀', 51), ('电视电影', 12), ('脱口秀', 10), ('挪威剧', 9), ('美剧', 8),
 ('丹麦剧', 8), ('综艺', 7), ('葡萄牙剧', 6), ('颁奖礼', 5), ('以色列剧', 4), ('菲律宾剧', 4), ('动漫', 4), ('瑞典剧', 4), ('新西兰剧', 4),
 ('神剧', 3), ('英剧', 3), ('短视频', 3), ('舞台剧', 3), ('MV', 3), ('演讲', 3), ('颁奖典礼', 3), ('比利时剧', 3), ('南非剧', 3), ('晨间剧', 2),
 ('短片', 2), ('荷兰剧', 2), ('新剧', 2), ('巴西电视剧', 2), ('爱尔兰剧', 2), ('汽车三贱客', 2), ('芬兰剧', 2), ('泰剧', 1), ('美剧 律政', 1),
 ('美剧/英剧', 1), ('小镇疑云(美版)', 1), ('动画片', 1), ('探案', 1), ('纪录', 1), ('演唱会', 1), ('冰岛剧', 1), ('深夜剧', 1), ('萌剧', 1),
 ('律政/剧情', 1), ('2013年BBC历史记录片', 1), ('催眠剧', 1), ('波兰剧', 1), ('幼教', 1), ('约旦', 1), ('闹剧', 1), ('浪漫/喜剧', 1), ('韩剧', 1),
 ('悬疑/罪案', 1), ('西剧', 1), ('BBC世界杯专题纪录片', 1), ('克罗地亚剧', 1), ('墨西哥剧', 1), ('惊悚', 1), ('阿拉伯剧', 1), ('委内瑞拉电视剧', 1),
 ('音乐会', 1), ('巴西剧', 1), ('新闻', 1), ('土耳其剧', 1), ('约旦剧', 1), ('发布会', 1), ('丹麦瑞典合拍', 1), ('捷克剧', 1), ('越南剧', 1),
 ('剧情', 1), ('墨西哥电视剧', 1), ('韩综', 1), ('花絮', 1)]

```

## 请求范例

全部使用 `size=1&douban=True`做为范例，响应结构如下

注意，由于并不是所有的资源都有豆瓣信息，因此有些可能douban字段为 `{}`

```json
{
  "data": [
    {
      "id": 30552,
      "cnname": "极限战队",
      "enname": "Ultraforce",
      "aliasname": "极端力量",
      "channel": "tv",
      "channel_cn": "美剧",
      "area": "美国",
      "show_type": "",
      "expire": "1610397126",
      "views": 0,
      "year": [
        2013
      ],
      "douban": {
        "name": "极限战队",
        "doubanId": 1295384,
        "doubanLink": "https://movie.douban.com/subject/1295384/",
        "posterLink": "https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2512733819.jpg",
        "posterData": "base64编码的图片",
        "resourceId": 30552,
        "rating": "7.9",
        "actors": [
          "卡斯帕·范·迪恩",
          "迪娜·迈耶",
          "丹妮丝·理查兹",
          "杰克·布塞",
          "尼尔·帕特里克·哈里斯",
          "克兰西·布朗",
          "塞斯·吉列姆",
          "帕特里克·茂顿",
          "迈克尔·艾恩塞德",
          "露·麦克拉纳罕",
          "马绍尔·贝尔",
          "埃里克·布鲁斯科特尔",
          "马特·莱文",
          "布蕾克·林斯利",
          "安东尼·瑞维瓦",
          "布兰达·斯特朗",
          "迪恩·诺里斯",
          "克里斯托弗·柯里",
          "莱诺尔·卡斯多夫",
          "罗伯特·斯莫特",
          "斯蒂芬·福特",
          "罗伯特·大卫·豪尔",
          "艾米·斯马特",
          "蒂莫西·奥门德森",
          "代尔·戴"
        ],
        "directors": [
          "保罗·范霍文"
        ],
        "genre": [
          "动作",
          "科幻",
          "惊悚",
          "冒险"
        ],
        "releaseDate": "1997-11-07",
        "episodeCount": "",
        "episodeDuration": "129 分钟",
        "writers": [
          "爱德华·诺麦尔",
          "罗伯特·A·海因莱因"
        ],
        "year": "1997",
        "introduction": "高中生瑞科（卡斯帕•凡•迪恩CasperVanDien饰）毕业后，在女友卡门（丹妮丝•理查兹DeniseRichards饰）的鼓动下，违背了父亲的意志，加入了机械化步兵学院，卡门亦加入了海军学院。在他们参加训练不久后，地球遭到了来自外星球的昆虫袭击。瑞科的亲人均惨遭杀害，卡门将拍摄到的影像传送给了瑞科。悲愤交加的瑞科率领部下投入到了对抗外星昆虫的战斗中。然而，军队低估了这些昆虫的实力。在一次遭遇战中，10万军队惨遭杀戮，只剩瑞科、卡门等几人侥幸逃生。瑞科亲眼目睹了恐怖的杀戮场面，意外获知了这些昆虫变得如此聪明、强大的秘密。瑞科意识到必须制造更先进的武器才能对付这些昆虫，人类的反击开始了！"
      }
    }
  ],
  "count": 9057
}
```

* 日剧 `http://127.0.0.1:8888/api/category?channel_cn=日剧`
* 国家为"美国"的资源 `http://127.0.0.1:8888/api/category?area=美国`
* 美国的纪录片 `http://127.0.0.1:8888/api/category?&area=美国&channel_cn=纪录片`
* 日本的电影 `http://127.0.0.1:8888/api/category?size=1&area=日本&channel=movie` 或 `channel_cn=电影`
* 动漫 `http://127.0.0.1:8888/api/category?size=1&channel_cn=动漫`

# 最新资源

* GET `/api/resource/latest`

可选URL参数 size，最大100，超过100无效。如 `http://127.0.0.1:8888/api/resource/latest?size=5` 即为获取最新5条数据

```json
{
  "data": [
    {
      "name": "速度与激情9-F9 (2021) (1080p) [BluRay] [HD FULL].avi 1.52 GB",
      "timestamp": "1623415867",
      "size": "1.52GB",
      "resource_id": 39894,
      "res_name": "速度与激情9",
      "date": "2021-06-11 20:51:07"
    },
    {
      "name": "洛基-E01",
      "timestamp": "1623415867",
      "size": "788.53MB",
      "resource_id": 41382,
      "res_name": "洛基",
      "date": "2021-06-11 20:51:07"
    },
    {
      "name": "致命女人-EP01",
      "timestamp": "1623415867",
      "size": "790MB",
      "resource_id": 38413,
      "res_name": "致命女人",
      "date": "2021-06-11 20:51:07"
    }
  ]
}
```