FROM python:3.8-alpine

RUN apk update && apk add  --no-cache tzdata ca-certificates
COPY requirements.txt /requirements.txt
RUN pip3 install  --no-cache-dir -r /requirements.txt && rm /requirements.txt
COPY ./yyetsbot /YYeTsBot/yyetsbot

ENV TZ=Asia/Shanghai
WORKDIR /YYeTsBot/yyetsbot
CMD ["python", "bot.py"]