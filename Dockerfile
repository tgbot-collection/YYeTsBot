FROM python:alpine

RUN apk update && apk add --no-cache tzdata alpine-sdk libxml2 libxslt-dev
COPY requirements.txt /requirements.txt
RUN pip3 install --no-cache-dir  -r /requirements.txt && rm /requirements.txt
COPY . /YYeTsBot/

ENV TZ=Asia/Shanghai

WORKDIR /YYeTsBot

CMD ["python", "bot.py"]

# usage
# docker build -t yyetsbot .
# docker run -d --restart=always -e TOKEN="TOKEN" -e USERNAME="" -e PASSWORD="" bennythink/yyetsbot