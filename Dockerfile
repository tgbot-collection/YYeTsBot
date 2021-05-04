FROM python:3.9-alpine as builder

RUN apk update && apk add  --no-cache tzdata ca-certificates alpine-sdk libressl-dev libffi-dev cargo
# build cryptography separately because it's very slow
RUN pip3 install --user cryptography==3.4.7

COPY requirements.txt /requirements.txt
RUN pip3 install  --user -r /requirements.txt && rm /requirements.txt



FROM python:3.9-alpine

COPY --from=builder /root/.local /usr/local
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY . /YYeTsBot
RUN apk update && apk add --no-cache libressl

ENV TZ=Asia/Shanghai
WORKDIR /YYeTsBot/yyetsbot
CMD ["python", "yyetsbot.py"]
