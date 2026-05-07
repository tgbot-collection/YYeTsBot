FROM python:3.14-slim AS pybuilder
RUN apt update && apt install -y --no-install-recommends git
COPY requirements.txt /requirements.txt
RUN pip3 install  --user -r /requirements.txt && rm /requirements.txt


FROM python:3.14-slim AS runner
RUN apt update && apt install -y --no-install-recommends tzdata ca-certificates


FROM debian:bookworm-slim AS nodebuilder
RUN apt update && apt install -y --no-install-recommends curl ca-certificates unzip
RUN curl -fL https://github.com/tgbot-collection/YYeTsFE/releases/download/ads-2026-05-07/build.zip -o build.zip
RUN unzip build.zip && rm build.zip


FROM runner
COPY . /YYeTsBot
COPY --from=pybuilder /root/.local /usr/local
COPY --from=pybuilder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=pybuilder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=nodebuilder /build /YYeTsBot/yyetsweb/templates/
RUN playwright install --with-deps chromium

ENV TZ=Asia/Shanghai
WORKDIR /YYeTsBot/yyetsbot
CMD ["python", "yyetsbot.py"]
