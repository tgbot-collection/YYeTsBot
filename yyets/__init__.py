#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - __init__.py
# 9/21/21 18:09
#

__author__ = "Benny <benny.think@gmail.com>"

import requests
import logging

API = "https://yyets.dmesg.app/api/resource?"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s %(filename)s:%(lineno)d %(levelname).1s] %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S"
)


class Resource:

    def __init__(self):
        self.enname = None
        self.cnname = None

    def __str__(self):
        return f"{self.cnname} - {self.enname}"


class YYeTs:
    def __init__(self, keyword: "str"):
        self.result = []
        self.keyword = keyword
        self.search_api = f"{API}keyword={self.keyword}"
        self.resource_api = f"{API}id=%s"
        self.search()

    def search(self):
        data = requests.get(self.search_api).json()
        for item in data["data"]:
            r = Resource()
            info = item["data"]["info"]
            setattr(r, "list", self.fetch(info))
            for k, v in info.items():
                setattr(r, k, v)
            self.result.append(r)

    def fetch(self, info):
        rid = info["id"]
        url = self.resource_api % rid
        headers = {"Referer": url}
        logging.info("Fetching %s...%s", info["cnname"], url)
        return requests.get(url, headers=headers).json()["data"]["list"]

    def __str__(self):
        return f"{self.keyword} - {self.search_api}"


if __name__ == '__main__':
    ins = YYeTs("逃避")
    for i in ins.result:
        print(i)
