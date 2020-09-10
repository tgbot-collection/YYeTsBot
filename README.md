# YYeTsBot
人人影视bot，[戳我使用](https://t.me/yyets_bot)

# 使用说明
直接发送想要看的剧集名称就可以了，会返回ed2k和磁力链接

# 截图

![](assets/1.jpg)

![](assets/2.jpg)

# 部署方法
## 使用docker
```bash
docker pull bennythink/yyetsbot
docker run -d --restart=always -e TOKEN="TOKEN"  bennythink/yyetsbot
```
根据情况，还可以 `-e USERNAME="1234"`

也可以自己构建docker image：
```bash
docker build -t yyetsbot .
```

## 常规方式
### 1. 环境
推荐使用Python 3.6+
```bash
pip install -r requirements.py
```
### 2. 配置TOKEN
修改`config.py`，把TOKEN修改为你的bot token, USERNAME PASSWORD看需求修改

也可以使用环境变量
### 3. 克隆&运行
```bash
git clone https://github.com/BennyThink/YYeTsBot
python /path/to/YYeTsBot/bot.py
```
### 4. systemd 单元文件
参考 `yyets.service`

# Credits
* [人人影视](http://www.zmz2019.com/)
* [追新番](http://www.zhuixinfan.com/main.php)
* [FIX字幕侠](http://www.zimuxia.cn/)
* [磁力下载站](http://oabt005.com/home.html)

# License
[MIT](LICENSE)