FROM python:alpine

RUN apk update && apk add alpine-sdk libxml2 libxslt-dev \
&& git clone https://github.com/BennyThink/YYeTsBot \
    && pip3 install -r /YYeTsBot/requirements.txt

WORKDIR /YYeTsBot


CMD python bot.py

# usage
# docker build -t yyetsbot .
# docker run -d --restart=always -e TOKEN="TOKEN" bennythink/yyetsbot