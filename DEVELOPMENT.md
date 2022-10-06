# 项目手册

# 网站部署方式

## 一键脚本

**支持amd64/arm64，请先安装 docker、docker-compose和curl**

**为了安全考虑，安装完成后程序将监听在 127.0.0.1 。如有需要请自行修改 `docker-compose.yml`的127.0.0.1为0.0.0.0**
### Linux/macOS：

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/tgbot-collection/YYeTsBot/master/scripts/install.sh)"
````

### Windows

请再安装一个 [git for windows](https://gitforwindows.org/)，然后桌面空白处右键，选择 `git bash here`
再然后

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/tgbot-collection/YYeTsBot/master/scripts/install.sh)"
````

## docker-compose

参考 `yyetsweb`目录下的 `README`

# bot

可以选择docker，也可以直接运行在机器上。

## docker-compose

* 参见 [这里](https://github.com/tgbot-collection/BotsRunner)
* 本目录下的 `docker-compose.yml` 也可以作为参考
* nginx reverse proxy可以[参考这里](https://github.com/BennyThink/WebsiteRunner)
* [参考这里获取数据库](yyetsweb/README.md)

```shell
# 启动数据库
docker-compose up -d mongo
# 导入数据库
docker yyets_mongo.gz 1234da:/tmp
# 进入容器
docker-compose exec mongo bash
mongorestore --gzip --archive=yyets_mongo.gz --nsFrom "share.*" --nsTo "zimuzu.*"
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

### 4. 运行

```bash
python /path/to/YYeTsBot/yyetsbot/bot.py
```

### 5. systemd 单元文件

参考 `yyets.service`

# 添加新的资源网站

欢迎各位开发提交新的资源网站！方法非常简单，重写 `BaseFansub`，实现`search_preview`和`search_result`，按照约定的格式返回数据。

然后把类名字添加到 `FANSUB_ORDER` 就可以了！是不是很简单！

# 防爬

## 1. referer

网站使用referer验证请求

## 2. rate limit

404的访问会被计数，超过10次会被拉入黑名单，持续3600秒，再次访问会持续叠加。

# 持续部署

使用[Docker Hub Webhook](https://docs.docker.com/docker-hub/webhooks/)
(顺便吐槽一句，这是个什么垃圾文档……自己实现validation吧)

参考listener [Webhook listener](https://github.com/tgbot-collection/Webhook)

# 归档资源下载

## Telegram 频道分享

* 包含了2021年1月11日为止的人人影视最新资源，MySQL为主。有兴趣的盆友可以用这个数据进行二次开发[戳我查看详情](https://t.me/mikuri520/668)
* 字幕侠离线数据库 [从这里下载](https://t.me/mikuri520/715)，这个数据比较粗糙，并且字幕侠网站还在，因此不建议使用这个

## 本地下载

如果无法访问Telegram，可以使用如下网址下载数据

* [网站实时数据，MongoDB](https://yyets.dmesg.app/data/yyets_mongo.gz)
* [MySQL](https://yyets.dmesg.app/data/yyets_mysql.zip)
* [SQLite](https://yyets.dmesg.app/data/yyets_sqlite.zip)

# API 文档

参考 [API.md](API.md)
