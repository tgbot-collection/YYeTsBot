# YYeTsBot

[![Build Status](https://travis-ci.com/tgbot-collection/YYeTsBot.svg?branch=master)](https://travis-ci.com/tgbot-collection/YYeTsBot)

[![codecov](https://codecov.io/gh/tgbot-collection/YYeTsBot/branch/master/graph/badge.svg?token=ZL1GCIF95D)](https://codecov.io/gh/tgbot-collection/YYeTsBot)

* 人人影视bot，[戳我使用](https://t.me/yyets_bot)

* 人人影视分享站，[戳我使用](https://yyets.dmesg.app/)

机器人和网站由我长期维护，如果遇到问题可以提issue。

- [使用说明](#使用说明)
- [命令](#命令)
- [截图](#截图)
    * [常规搜索](#常规搜索)
    * [资源分享站截图](#资源分享站截图)
    * [指定字幕组搜索](#指定字幕组搜索)
- [部署运行](#部署运行)
    * [docker-compose](#docker-compose)
    * [常规方式](#常规方式)
        + [1. 环境](#1-环境)
        + [2. 配置TOKEN](#2-配置TOKEN)
        + [3. 导入数据（可选）](#3-导入数据可选)
        + [4. 运行](#4-运行)
        + [5. systemd 单元文件](#5-systemd-单元文件)
        + [6. 网站部署运行方式](#6-网站部署运行方式)
- [TODO](#todo)
- [归档资源下载](#归档资源下载)
- [开发](#开发)
    * [添加新的资源网站](#添加新的资源网站)
    * [health check](#health-check)
- [Credits](#credits)
- [支持我](#支持我)
- [License](#license)

# 使用说明

直接发送想要看的剧集名称就可以了，可选分享网页或者链接（ed2k和磁力链接）。

支持字幕侠、人人影视（目前人人影视官网无法打开，暂时无法使用）、人人影视离线资源

搜索资源时，会按照我预定的优先级（字幕侠、人人影视离线）进行搜索，当然也可以使用命令强制某个字幕组，如 `/yyets_offline 逃避可耻`

**由于译名的不同，建议输入部分译名，然后从列表中进行选择。比如说想看权力的游戏第四季，那么直接搜索"权力的游戏"就可以了。**

# 命令

```
start - 开始使用
help - 帮助
credits - 致谢
ping - 运行状态
settings - 获取公告
zimuxia_offline - 字幕侠离线数据
zimuxia_online - 字幕侠在线数据  
yyets_online - 人人影视在线数据  
yyets_offline - 人人影视离线数据
```

# 截图

## 常规搜索

![](assets/1.png)

## 资源分享站截图

~~目前使用的是我的 Cloudflare Worker Site~~

![](assets/2.png)

## 指定字幕组搜索

目前只支持YYeTsOffline和ZimuxiaOnline

![](assets/3.png)

# 部署运行

## docker-compose

* 参见 [这里](https://github.com/tgbot-collection/BotsRunner)
* 本目录下的 `docker-compose.yml` 也可以作为参考
* nginx reverse proxy可以[参考这里](https://github.com/BennyThink/WebsiteRunner)
* [参考这里获取数据库](web/README.md)

```shell
# 启动数据库
docker-compose up -d mongo
# 导入数据库
docker cp db.tgz 1234da:/tmp
# 进入容器
docker-compose exec mongo bash
tar xf db.tgz
mongorestore
exit
# 开启服务
docker-compose up -d
```

## 常规方式

### 1. 环境

推荐使用Python 3.6+，环境要求

* redis
* 可选MongoDB

```bash
pip install -r requirements.txt
```

### 2. 配置TOKEN

修改`config.py`，根据需求修改如下配置项

* TOKEN：bot token
* USERNAME：人人影视的有效的用户名
* PASSWORD ：人人影视的有效的密码
* MAINTAINER：维护者的Telegram UserID
* REDIS：redis的地址，一般为localhost
* MONGODB: mongodb的地址

### 3. 导入数据（可选）

如果使用yyets，那么需要导入数据到MongoDB。可以在将数据导入到MySQL之后使用如下脚本导入数据到MongoDB

```shell
python3 web/prepare/convert_db.py
```

**不再兼容旧版本数据**

### 4. 运行

```bash
python /path/to/YYeTsBot/yyetsbot/bot.py
```

### 5. systemd 单元文件

参考 `yyets.service`

### 6. 网站部署运行方式

参考 `worker`和`web`目录下的 `README`

# TODO

- [x] 添加对FIX的支持
- [x] 文件/函数重命名，类化
- [x] 优先字幕组顺序设置 - 动态设置
- [x] 添加个人喜好搜索
- [x] 整理fix资源：初步完成
- [x] 独立网站
- [ ] test case...啊不想写
- [ ] 独立网站网页优化
- [ ] 爬取并同步[追新番](web/追新番爬取策略.md)

# 归档资源下载

* 包含了2021年1月11日为止的人人影视最新资源，有兴趣的盆友可以用这个数据进行二次开发[戳我查看详情](https://t.me/mikuri520/668)
* 字幕侠离线数据库 [从这里下载](https://t.me/mikuri520/715)，这个数据比较粗糙，并且字幕侠网站还在，因此不建议使用这个

# 开发

如何参与开发、具体API接口，可以 [参考这个文档](DEVELOPMENT.md)

# Credits

* [人人影视](http://www.zmz2019.com/)
* [追新番](http://www.zhuixinfan.com/main.php)
* [磁力下载站](http://oabt005.com/home.html)
* [FIX字幕侠](https://www.zimuxia.cn/)

# 支持我

觉得本项目对你有帮助？你可以通过以下方式表达你的感受：

* 感谢字幕组
* 点一个star🌟和fork🍴
* 宣传，使用，提交问题报告
* 收藏[我的博客](https://dmesg.app/)
* [Telegram Channel](https://t.me/mikuri520)
* 捐助我，[给我买杯咖啡？](https://www.buymeacoffee.com/bennythink)

# 持续部署

使用[Docker Hub Webhook](https://docs.docker.com/docker-hub/webhooks/)
(顺便吐槽一句，这是个什么垃圾文档……自己实现validation吧)

参考listener [Webhook listener](https://github.com/tgbot-collection/Webhook)

# License

[MIT](LICENSE)
