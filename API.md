# 需求与待开发功能

## FE

- [x] group为admin特殊显示，评论接口已返回group信息
- [x] 评论楼中楼
- [x] 联合搜索，当本地数据库搜索不到数据时，会返回extra字段
- [x] 最新评论
- [x] 公告
- [ ] 评论通知（浏览器通知）

# BE

- [x] 联合搜索：字幕侠、new字幕组、追新番
- [x] grafana面板
- [x] 豆瓣接口
- [ ] 用户体系（添加邮箱，邮件支持，找回密码）
- [ ] 评论通知，需要新接口
- [ ] 添加资源API

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
  ]
}
```

# 获取全部剧集名称

* GET `/api/name`
* GET `/api/name?human=1` 人类可读

# 添加或删除收藏

* PATCH `/api/user`，提交json，字段 `resource_id`

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