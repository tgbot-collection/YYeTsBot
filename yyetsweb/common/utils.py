#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - utils.py
# 6/16/21 21:42
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib
import json
import logging
import os
import pathlib
import re
import smtplib
import time
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from hashlib import sha256

import coloredlogs
import pytz
import requests
from akismet import Akismet
from jinja2 import Template

from databases.base import Redis


def setup_logger():
    coloredlogs.install(
        level=logging.INFO,
        fmt="[%(asctime)s %(filename)s:%(lineno)d %(levelname).1s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def hide_phone(data: list):
    for item in data:
        if item["username"].isdigit() and len(item["username"]) == 11:
            item["hash"] = sha256(item["username"].encode("u8")).hexdigest()
            item["username"] = mask_phone(item["username"])
    return data


def mask_phone(num):
    return re.sub(r"(\d{3})\d{4}(\d{4})", r"\g<1>****\g<2>", num)


def ts_date(ts=None):
    # Let's always set the timezone to CST
    timestamp = ts or time.time()
    return datetime.fromtimestamp(timestamp, pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")


def _format_addr(s):
    name, addr = parseaddr(s)
    return formataddr((Header(name, "utf-8").encode(), addr))


def generate_body(context):
    template = pathlib.Path(__file__).parent.parent.joinpath("templates", "email_template.html")
    with open(template) as f:
        return Template(f.read()).render(**context)


def send_mail(to: str, subject: str, context: dict):
    user = os.getenv("email_user")
    password = os.getenv("email_password")
    host = os.getenv("email_host", "localhost")
    port = os.getenv("email_port", "1025")  # mailhog
    from_addr = os.getenv("from_addr", "hello@yyets.click")

    msg = MIMEText(generate_body(context), "html", "utf-8")
    msg["From"] = _format_addr("YYeTs <%s>" % from_addr)
    msg["To"] = _format_addr(to)
    msg["Subject"] = Header(subject, "utf-8").encode()

    logging.info("logging to mail server...")
    if port == "1025":
        server = smtplib.SMTP(host, int(port))
    else:
        server = smtplib.SMTP_SSL(host, int(port))
    server.login(user, password)
    logging.info("sending email to %s", to)
    server.sendmail(from_addr, [to], msg.as_string())
    server.quit()


def check_spam(ip, ua, author, content) -> int:
    # 0 means okay
    token = os.getenv("askismet")
    whitelist: "list" = os.getenv("whitelist", "").split(",")
    if author in whitelist:
        return 0
    if token:
        with contextlib.suppress(Exception):
            akismet = Akismet(token, blog="https://yyets.click/")

            return akismet.check(
                ip,
                ua,
                comment_author=author,
                blog_lang="zh_cn",
                comment_type="comment",
                comment_content=content,
            )
    return 0


class Cloudflare(Redis):
    key = "cf-blacklist-ip"
    expire = "cf-expire"

    def __init__(self):
        self.account_id = "e8d3ba82fe9e9a41cceb0047c2a2ab4f"
        self.item_id = "3740654e0b104053b3e5d0a71fe87b33"
        self.endpoint = "https://api.cloudflare.com/client/v4/accounts/{}/rules/lists/{}/items".format(
            self.account_id, self.item_id
        )
        self.session = requests.Session()
        self.session.headers.update({"Authorization": "Bearer %s" % os.getenv("CF_TOKEN")})
        super().__init__()

    def get_old_ips(self) -> dict:
        cache = self.r.get(self.key)
        if cache:
            cache = json.loads(cache)
            logging.info("Cache found with %s IPs", len(cache))
            if len(cache) > 10000:
                return cache[:5000]
            return cache
        else:
            data = self.session.get(self.endpoint).json()
            result = data.get("result", [])
            cursor = data.get("result_info", {}).get("cursors", {}).get("after")
            while cursor:
                logging.info("Fetching next page with cursor %s", cursor)
                data = self.session.get(self.endpoint, params={"cursor": cursor}).json()
                result.extend(data["result"])
                cursor = data.get("result_info", {}).get("cursors", {}).get("after")
            logging.info("Got %s IPs", len(result))
            return result

    def ban_new_ip(self, ip):
        if ":" in ip:
            ip = ip.rsplit(":", 4)[0] + "::/64"
        old_ips = [d["ip"] for d in self.get_old_ips()]
        old_ips.append(ip)
        body = [{"ip": i} for i in set(old_ips)]
        self.r.set(self.key, json.dumps(body))
        if not self.r.exists(self.expire):
            resp = self.session.put(self.endpoint, json=body)
            logging.info(resp.json())
            self.r.set(self.expire, 1, ex=120)

    def clear_fw(self):
        logging.info("Clearing firewall rules")
        self.session.put(self.endpoint, json=[{"ip": "192.168.3.1"}])
        logging.info("Clearing cache from redis")
        self.r.delete(self.key)


if __name__ == "__main__":
    cf = Cloudflare()
    cf.ban_new_ip("192.168.1.1")
