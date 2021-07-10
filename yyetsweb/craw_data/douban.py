#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - douban.py
# 7/10/21 22:59
#

__author__ = "Benny <benny.think@gmail.com>"

from bs4 import BeautifulSoup
import re

with open("douban_detail.html") as f:
    detail_html = f.read()
soup = BeautifulSoup(detail_html, 'html.parser')

intro = soup.find_all("span", property="v:summary")[0].text
i = re.sub(r"\s", "", intro)

print(i)
