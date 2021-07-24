#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - douban.py
# 7/10/21 22:59
#

__author__ = "Benny <benny.think@gmail.com>"

import re

from bs4 import BeautifulSoup

from Mongo import DoubanMongoResource

with open("douban_detail.html") as f:
    detail_html = f.read()
soup = BeautifulSoup(detail_html, 'html.parser')


douban = DoubanMongoResource()
rid = 27238
douban.find_douban(rid)
