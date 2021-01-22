# YYeTsBot

人人影视bot，[戳我使用](https://t.me/yyets_bot)

此机器人长期维护，如果遇到问题可以发送报告给我。

# 使用说明

直接发送想要看的剧集名称就可以了，可选分享网页或者链接（ed2k和磁力链接）。

支持字幕侠、人人影视（目前人人影视官网无法打开，暂时无法使用）、人人影视离线资源
支持多个字幕组、多种资源类型的优先级搜索。

**由于译名的不同，建议输入部分译名，然后从列表中进行选择。比如说想看权力的游戏第四季，那么直接搜索"权力的游戏"就可以了。**

# commands

```
start - 开始使用
help - 帮助
credits - 致谢
ping - 运行状态
settings - 获取公告
ZimuxiaOffline - 搜索字幕侠离线数据 还没做好
ZimuxiaOnline - 搜索字幕侠在线数据  这个也还没做
YYeTsOffline - 搜索人人影视离线数据  你猜的没错，这个也没做
YYeTsOnline - 搜索人人影视在线数据  想做也做不了了啊！
```

# 截图

![](assets/1.png)

![](assets/2.png)

# docker-compose 部署方法
参见 [这里](https://github.com/tgbot-collection/BotsRunner)

# 常规方式

## 1. 环境

推荐使用Python 3.6+，需要安装redis `apt install redis`，根据个人情况可以使用virtualenv

如果想使用yyets离线数据库，那么还需要 mongodb，并且[从这里下载数据库](https://t.me/mikuri520/675)并恢复

```bash
pip install -r requirements.py
```

### 2. 配置TOKEN

修改`config.py`，根据需求修改如下配置项

* TOKEN：bot token
* USERNAME：人人影视的有效的用户名
* PASSWORD ：人人影视的有效的密码
* MAINTAINER：维护者的Telegram UserID
* REDIS：redis的地址，一般为localhost
* MONGODB: mongodb的地址

### 3. 运行

```bash
python /path/to/YYeTsBot/bot.py
```

### 4. systemd 单元文件

参考 `yyets.service`

# TODO
- [x] 添加对FIX的支持
- [x] 文件/函数重命名，类化
- [x] 优先字幕组顺序设置 - 动态设置
- [ ] 添加个人喜好搜索
- [ ] 整理fix资源
- [ ] test case...啊不想写


# 归档资源下载

包含了2021年1月11日为止的最新资源，有兴趣的盆友可以用这个数据进行二次开发
[戳我查看详情](https://t.me/mikuri520/668)

# 开发
## 添加新的资源网站
欢迎各位开发提交新的资源网站！方法非常简单，重写 `BaseFansub`，按照约定的格式返回数据。
然后把类名字添加到 `FANSUB_ORDER` 就可以了！是不是很简单！
## health check
有时不知为何遇到了bot卡死，无任何反馈。😂这个时候需要client api了😂

# Credits

* [人人影视](http://www.zmz2019.com/)
* [追新番](http://www.zhuixinfan.com/main.php)
* [磁力下载站](http://oabt005.com/home.html)
* [FIX字幕侠](https://www.zimuxia.cn/)

# License

[MIT](LICENSE)
