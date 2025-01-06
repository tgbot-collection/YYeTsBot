FROM python:3.12-alpine AS pybuilder
RUN apk update && apk add  --no-cache tzdata ca-certificates alpine-sdk libressl-dev libffi-dev cargo && \
    apk add tiff-dev jpeg-dev openjpeg-dev zlib-dev freetype-dev lcms2-dev \
    libwebp-dev tcl-dev tk-dev harfbuzz-dev fribidi-dev libimagequant-dev libxcb-dev libpng-dev

COPY requirements.txt /requirements.txt
RUN pip3 install  --user -r /requirements.txt && rm /requirements.txt


FROM python:3.12-alpine AS runner
RUN apk update && apk add --no-cache libressl jpeg-dev openjpeg-dev libimagequant-dev tiff-dev freetype-dev libxcb-dev


FROM alpine AS nodebuilder
RUN apk add curl jq
RUN wget $(curl -s https://api.github.com/repos/tgbot-collection/YYeTsFE/releases/tags/burn-20240106 | jq -r '.assets[] | select(.name == "build.zip") | .browser_download_url')
RUN unzip build.zip && rm build.zip

FROM runner
RUN apk add mongodb-tools mysql-client
COPY . /YYeTsBot

COPY --from=pybuilder /root/.local /usr/local
COPY --from=pybuilder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=pybuilder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=nodebuilder /build /YYeTsBot/yyetsweb/templates/

ENV TZ=Asia/Shanghai
WORKDIR /YYeTsBot/yyetsbot
CMD ["python", "yyetsbot.py"]
