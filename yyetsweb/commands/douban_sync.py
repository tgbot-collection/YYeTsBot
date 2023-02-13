#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - douban.py
# 7/11/21 10:17
#

__author__ = "Benny <benny.think@gmail.com>"

import contextlib
import logging
import pathlib
import sys

import requests
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
lib_path = pathlib.Path(__file__).parent.parent.resolve().as_posix()
sys.path.append(lib_path)
from Mongo import DoubanMongoResource


def sync_douban():
    douban = DoubanMongoResource()
    session = requests.Session()
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    session.headers.update({"User-Agent": ua})

    yyets_data = douban.db["yyets"].find()
    douban_data = douban.db["douban"].find()

    id1 = [i["data"]["info"]["id"] for i in yyets_data]
    id2 = [i["resourceId"] for i in douban_data]
    rids = list(set(id1).difference(id2))
    logging.info("resource id complete %d", len(rids))
    for rid in tqdm(rids):
        with contextlib.suppress(Exception):
            d = douban.find_douban(rid)
            logging.info("Processed %s, length %d", rid, len(d))

    logging.info("ALL FINISH!")


if __name__ == '__main__':
    sync_douban()