FROM python:3.9-alpine as builder

RUN apk update && apk add  --no-cache tzdata ca-certificates alpine-sdk libressl-dev libffi-dev cargo && \
    apk add tiff-dev jpeg-dev openjpeg-dev zlib-dev freetype-dev lcms2-dev \
    libwebp-dev tcl-dev tk-dev harfbuzz-dev fribidi-dev libimagequant-dev libxcb-dev libpng-dev

COPY requirements.txt /requirements.txt
RUN pip3 install  --user -r /requirements.txt && rm /requirements.txt



FROM python:3.9-alpine

COPY --from=builder /root/.local /usr/local
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY . /YYeTsBot
RUN apk update && apk add --no-cache libressl jpeg-dev openjpeg-dev libimagequant-dev tiff-dev freetype-dev libxcb-dev

ENV TZ=Asia/Shanghai
WORKDIR /YYeTsBot/yyetsbot
CMD ["python", "yyetsbot.py"]
