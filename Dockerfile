FROM python:3.9-alpine3.13 as pybuilder
RUN apk update && apk add  --no-cache tzdata ca-certificates alpine-sdk libressl-dev libffi-dev cargo && \
    apk add tiff-dev jpeg-dev openjpeg-dev zlib-dev freetype-dev lcms2-dev \
    libwebp-dev tcl-dev tk-dev harfbuzz-dev fribidi-dev libimagequant-dev libxcb-dev libpng-dev

COPY requirements.txt /requirements.txt
RUN pip3 install  --user -r /requirements.txt && rm /requirements.txt


FROM python:3.9-alpine3.13 as runner
RUN apk update && apk add --no-cache libressl jpeg-dev openjpeg-dev libimagequant-dev tiff-dev freetype-dev libxcb-dev


FROM node:lts-alpine as nodebuilder
WORKDIR /build
ARG env
RUN apk add git
COPY YYeTsFE/package.json /build/
COPY YYeTsFE/yarn.lock /build/
COPY scripts/dev_robots.sh /tmp/
RUN yarn --network-timeout 1000000
COPY YYeTsFE /build/
RUN if [ "$env" = "dev" ]; then echo "dev build"; yarn build; sh /tmp/dev_robots.sh; else echo "prod build"; yarn run release; fi


FROM runner
COPY . /YYeTsBot
COPY --from=pybuilder /root/.local /usr/local
COPY --from=pybuilder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=pybuilder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=nodebuilder /build/build /YYeTsBot/yyetsweb/templates/

ENV TZ=Asia/Shanghai
WORKDIR /YYeTsBot/yyetsbot
CMD ["python", "yyetsbot.py"]
