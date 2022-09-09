#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - utils.py
# 6/16/21 21:42
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib
import logging
import os
import smtplib
import time
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

import requests
from akismet import Akismet


def ts_date(ts=None):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _format_addr(s):
    name, addr = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), addr))


def send_mail(to: str, subject: str, body: str):
    user = os.getenv("email_user")
    password = os.getenv("email_password")
    host = os.getenv("email_host") or "localhost"
    port = os.getenv("email_port") or "1025"  # mailhog
    from_addr = os.getenv("from_addr") or "yyets@dmesg.app"

    msg = MIMEText(body, 'html', 'utf-8')
    msg['From'] = _format_addr('YYeTs <%s>' % from_addr)
    msg['To'] = _format_addr(to)
    msg['Subject'] = Header(subject, 'utf-8').encode()

    if port == "1025":
        server = smtplib.SMTP(host, int(port))
    else:
        server = smtplib.SMTP_SSL(host, int(port))
    server.login(user, password)
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
            akismet = Akismet(token, blog="https://yyets.dmesg.app/")

            return akismet.check(ip, ua, comment_author=author, blog_lang="zh_cn",
                                 comment_type="comment",
                                 comment_content=content)
    return 0


class Cloudflare:
    def __init__(self):
        self.zone_id = "b8e2d2fa75c6f7dc3c2e478e27f3061b"
        self.filter_id = "9e1e9139bcbe400c8b2620ac117a77d8"
        self.endpoint = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/filters/{self.filter_id}"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": "Bearer %s" % os.getenv("CF_TOKEN")})

    def get_old_expr(self):
        return self.session.get(self.endpoint).json()["result"]["expression"]

    def ban_new_ip(self, ip):
        logging.info("Blacklisting IP %s", ip)
        expr = self.get_old_expr()
        if ip not in expr:
            body = {
                "id": self.filter_id,
                "paused": False,
                "expression": f"{expr} or (ip.src eq {ip})"
            }
            resp = self.session.put(self.endpoint, json=body)
            logging.info(resp.json())

    def clear_fw(self):
        logging.info("Clearing firewall rules")
        body = {
            "id": self.filter_id,
            "paused": False,
            "expression": "(ip.src eq 192.168.2.1)"
        }
        self.session.put(self.endpoint, json=body)


if __name__ == '__main__':
    cf = Cloudflare()
    cf.clear_fw()
    cf.ban_new_ip("3.3.3.3")
