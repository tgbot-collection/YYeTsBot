# YYeTsBot

人人影视bot，[戳我使用](https://t.me/yyets_bot)

此机器人长期维护，如果遇到问题可以发送报告给我。

# 使用说明

直接发送想要看的剧集名称就可以了，可选分享网页或者链接（ed2k和磁力链接）。

**由于译名的不同，建议输入部分译名，然后从列表中进行选择。比如说想看权力的游戏第四季，那么直接搜索"权力的游戏"就可以了。**

# commands

```
start - 开始使用
help - 帮助
credits - 致谢
ping - 运行状态
settings - 获取公告
ZimuxiaOffline - 搜索字幕侠离线数据
ZimuxiaOnline - 搜索字幕侠在线数据
YYeTsOffline - 搜索人人影视离线数据
YYeTsOnline - 搜索人人影视在线数据
```

# 截图

![](assets/1.png)

![](assets/2.png)

# 部署方法

## 使用docker

参见 [这里](https://github.com/tgbot-collection/BotsRunner)

## 常规方式

### 1. 环境

推荐使用Python 3.6+，需要安装redis `apt install redis`，根据个人情况可以使用virtualenv

```bash
pip install -r requirements.py
```

### 2. 配置TOKEN

修改`config.py`，根据需求修改如下配置项

* TOKEN：bot token
* USERNAME：人人影视的有效的用户名
* PASSWORD ：人人影视的有效的密码
* PROXY ：是否需要使用代理 格式 `http://userproxy:password@proxy_address:port`
* MAINTAINER：维护者的Telegram UserID
* REDIS：redis的地址，一般为localhost

### 3. 运行

```bash
python /path/to/YYeTsBot/bot.py
```

### 4. systemd 单元文件

参考 `yyets.service`

# TODO
- [x] 添加对FIX的支持
- [x] 文件/函数重命名，类化
- [x] 优先字幕组顺序设置
- [ ] 整理fix资源
- [ ] test case...啊不想写

参见分支 `zimuxia`

# 归档资源下载

包含了2021年1月11日为止的最新资源，有兴趣的盆友可以用这个数据进行二次开发
[戳我查看详情](https://t.me/mikuri520/668)

# Credits

* [人人影视](http://www.zmz2019.com/)
* [追新番](http://www.zhuixinfan.com/main.php)
* [磁力下载站](http://oabt005.com/home.html)

# License

[MIT](LICENSE)
