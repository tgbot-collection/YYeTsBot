#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - zimuxia.py
# 2/5/21 12:44
#

__author__ = "Benny <benny.think@gmail.com>"

import requests
import random
import time
import json
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import tqdm
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')

list_url = "https://www.zimuxia.cn/%e6%88%91%e4%bb%ac%e7%9a%84%e4%bd%9c%e5%93%81?set={}"
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"

s = requests.session()
s.headers.update({"User-Agent": ua})

data = []


def get_list():
    for index in tqdm.trange(1, 89):
        time.sleep(random.random())
        url = list_url.format(index)
        list_html = s.get(url).text
        get_episode(list_html)


def get_episode(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    episodes = soup.find_all("div", class_="pg-item")

    for block in episodes:
        url = block.a['href']
        name = unquote(url).split("https://www.zimuxia.cn/portfolio/")[1]
        logging.info("fetching %s", name)
        t = {"url": url, "name": name, "data": s.get(url).text}
        data.append(t)


def write_json():
    with open("result.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    get_list()
    write_json()
