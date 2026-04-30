#!/usr/bin/env python3
# coding: utf-8
import contextlib
import random

# YYeTsBot - comments_check.py

import re
import os
import time
from abc import ABC, abstractmethod
from typing import Union
from urllib.parse import urlparse

from pymongo import MongoClient
from bson import ObjectId
import requests
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
session = requests.Session()
session.headers.update(
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"}
)

URL_RE = re.compile(r"https?://[^\s<>'\"，。；、]+", re.I)


class LinkChecker(ABC):
    domains = []

    def __init__(self, url: str):
        self.url = url

    def match(self) -> bool:
        host = urlparse(self.url).netloc.lower()
        return any(d in host for d in self.domains)

    @abstractmethod
    def is_valid(self) -> bool:
        """
        return True  = link is still valid
        return False = link is invalid/dead
        """
        raise NotImplementedError


class QuarkChecker(LinkChecker):
    domains = ["pan.quark.cn"]
    api = "https://drive-h.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc&uc_param_str="

    @property
    def share_id(self):
        # https://pan.quark.cn/s/45cfdf4c5d8#/list/share
        parsed = urlparse(self.url)
        # path: /s/45cfdf4c5d8
        parts = parsed.path.strip("/").split("/")

        share_id = parts[1] if len(parts) >= 2 and parts[0] == "s" else None
        logging.info("Share id for %s is %s", self.url, share_id)
        return share_id

    def is_valid(self) -> bool:
        with contextlib.suppress(Exception):
            req = session.post(self.api, json={"pwd_id": self.share_id})
            if req.status_code == 404:
                logging.warning("Invalid share_id: %s", self.share_id)
                return False
        return True


class BaiduChecker(LinkChecker):
    domains = ["pan.baidu.com"]

    def is_valid(self) -> bool:
        with contextlib.suppress(Exception):
            html = session.get(self.url).text
            if "不存在" in html or "失效" in html or "过期" in html:
                return False
        return True


class AliyunChecker(LinkChecker):
    domains = ["aliyundrive.com", "alipan.com"]
    api = "https://api.aliyundrive.com/adrive/v3/share_link/get_share_by_anonymous?share_id="

    @property
    def share_id(self):
        # https://www.aliyundrive.com/s/7LzKr2WFhm6
        parsed = urlparse(self.url)
        parts = parsed.path.rstrip("/").split("/")
        share_id = parts[-1]
        logging.info("Share id for %s is %s", self.url, share_id)
        return share_id

    def is_valid(self) -> bool:
        with contextlib.suppress(Exception):
            req = session.post(self.api, json={"share_id": self.share_id})
            if req.status_code == 400:
                logging.warning("Invalid share_id: %s", self.share_id)
                return False
        return True


class XunleiChecker(LinkChecker):
    domains = ["pan.xunlei.com"]

    def is_valid(self) -> bool:
        # TODO: implement xunlei check
        return True


def extract_urls(content: str) -> list[str]:
    if not content:
        return []
    return URL_RE.findall(content)


def get_checker(url: str) -> Union[LinkChecker, None]:
    checkers = [
        QuarkChecker(url),
        BaiduChecker(url),
        AliyunChecker(url),
        XunleiChecker(url),
    ]
    for checker in checkers:
        if checker.match():
            return checker
    return None


def comment_has_invalid_link(content: str) -> bool:
    urls = extract_urls(content)

    for url in urls:
        checker = get_checker(url)
        if not checker:
            continue

        try:
            if not checker.is_valid():
                time.sleep(random.random() * 3)
                # not valid
                return True
        except Exception as e:
            print(f"[WARN] check failed url={url}, error={e}")
            # 保守一点：检测失败不标 invalid
            continue

    return False


def comment_check():
    mongo_client = MongoClient(
        host=os.getenv("MONGO", "localhost"),
        connect=True,
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000,
        maxPoolSize=300,
        minPoolSize=50,
        maxIdleTimeMS=600000,
    )
    db = mongo_client["zimuzu"]
    col = db["comment"]

    cursor = (
        col.find(
            {
                "content": {"$regex": "https?://"},
                "invalid": {"$ne": True},
            },
            {
                "_id": 1,
                "content": 1,
            },
        ).sort({"_id": -1})
        # .limit(100)
    )

    checked = 0
    marked = 0

    for doc in tqdm(cursor):
        checked += 1
        content = doc.get("content", "")

        if comment_has_invalid_link(content):
            col.update_one(
                {"_id": doc["_id"]},
                {"$set": {"invalid": True}},
            )
            marked += 1
            print(f"[INVALID] {doc['_id']}")

    logging.info(f"checked={checked}, marked_invalid={marked}")


if __name__ == "__main__":
    comment_check()
