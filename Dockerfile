FROM python:alpine

RUN apk update && apk add --no-cache tzdata alpine-sdk git libxml2 libxslt-dev \
&& git clone https://github.com/BennyThink/YYeTsBot \
&& pip3 install --no-cache-dir  -r /YYeTsBot/requirements.txt

ENV TZ=Asia/Shanghai

WORKDIR /YYeTsBot


CMD ["python", "bot.py"]

# usage
# docker build -t yyetsbot .
# docker run -d --restart=always -e TOKEN="TOKEN" -e USERNAME="" -e PASSWORD="" bennythink/yyetsbot