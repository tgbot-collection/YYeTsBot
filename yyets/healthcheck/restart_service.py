#!/usr/local/bin/python3
# coding: utf-8

# untitled - restart_service.py
# 9/18/21 11:54
#

__author__ = "Benny <benny.think@gmail.com>"

import logging.handlers
import subprocess

import requests

filename = "yyets_restart.log"
formatter = logging.Formatter("[%(asctime)s %(filename)s:%(lineno)d %(levelname).1s] %(message)s", "%Y-%m-%d %H:%M:%S")
handler = logging.handlers.RotatingFileHandler(filename, maxBytes=1024 * 1024 * 100)
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

URL = "https://yyets.click/api/top"
# URL = "https://www.baidu.com/"
req = requests.get(URL)

if req.status_code != 200:
    logger.error("error! %s", req)
    cmd = "/usr/bin/docker-compose -f /home/WebsiteRunner/docker-compose.yml restart mongo yyets-web nginx"
    subprocess.check_output(cmd.split())
else:
    logger.info("YYeTs is running %s", req)
