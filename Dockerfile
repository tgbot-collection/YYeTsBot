FROM python:3.9-alpine3.13 as pybuilder

RUN apk update && apk add  --no-cache tzdata ca-certificates alpine-sdk libressl-dev libffi-dev cargo && \
    apk add tiff-dev jpeg-dev openjpeg-dev zlib-dev freetype-dev lcms2-dev \
    libwebp-dev tcl-dev tk-dev harfbuzz-dev fribidi-dev libimagequant-dev libxcb-dev libpng-dev

COPY requirements.txt /requirements.txt
RUN pip3 install  --user -r /requirements.txt && rm /requirements.txt


FROM python:3.9-alpine3.13 as runner
RUN apk update && apk add --no-cache libressl jpeg-dev openjpeg-dev libimagequant-dev tiff-dev freetype-dev libxcb-dev


FROM node:alpine as nodebuilder
ARG env
WORKDIR /YYeTsBot/YYeTsFE/
RUN apk add git
COPY YYeTsFE/package.json /YYeTsBot/YYeTsFE/
COPY YYeTsFE/yarn.lock /YYeTsBot/YYeTsFE/
RUN yarn --network-timeout 100000
COPY YYeTsFE /YYeTsBot/YYeTsFE/
COPY .git/modules /YYeTsBot/.git/modules/
RUN echo "gitdir: ../.git/modules/YYeTsFE" > .git
RUN if [ "$env" = "dev" ]; then echo "dev build";yarn build; else echo "prod build"; yarn run release; fi


FROM runner
COPY . /YYeTsBot
COPY --from=pybuilder /root/.local /usr/local
COPY --from=pybuilder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=pybuilder /usr/share/zoneinfo /usr/share/zoneinfo
RUN true
COPY --from=nodebuilder /YYeTsBot/YYeTsFE/build /YYeTsBot/yyetsweb

ENV TZ=Asia/Shanghai
WORKDIR /YYeTsBot/yyetsbot
CMD ["python", "yyetsbot.py"]
