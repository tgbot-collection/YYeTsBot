#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - utils.py
# 6/16/21 21:42
#

__author__ = "Benny <benny.think@gmail.com>"

import os
import smtplib
import time

from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr


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
        server = smtplib.SMTP(host, port)
    else:
        server = smtplib.SMTP_SSL(host, port)
    server.login(user, password)
    server.sendmail(from_addr, [to], msg.as_string())
    server.quit()


if __name__ == '__main__':
    send_mail("benny.think@gmail.com", "subj", 'aaaa<br>bbb')
