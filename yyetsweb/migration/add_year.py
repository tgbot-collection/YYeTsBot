#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - add_year.py
# 4/8/21 18:39
#

__author__ = "Benny <benny.think@gmail.com>"

import pymongo
import time
import re
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)


def ts_year(ts: str) -> int:
    return int(time.strftime("%Y", time.localtime(int(ts))))


def extract_year(name: str) -> int:
    try:
        r = int(re.findall(r"\.(19\d{2}|20\d{2})\.", name)[0])
    except:
        r = None
    return r


mongo_client = pymongo.MongoClient()
col = mongo_client["zimuzu"]["yyets"]

data = col.find()

for datum in tqdm(data):
    list_data = datum["data"]["list"]
    translate_year = []
    filename_year = []
    for single in list_data:
        dl = single["items"].values()
        for i in dl:
            for j in i:
                if d := ts_year(j["dateline"]):
                    translate_year.append(d)
                if d := extract_year(j["name"]):
                    filename_year.append(d)

    translate_year = list(set(translate_year))
    filename_year = list(set(filename_year))  # more accurate

    final_year = []

    if filename_year:
        final_year = filename_year.copy()
    elif translate_year:
        final_year = translate_year
    _id = datum["data"]["info"]["id"]
    name = datum["data"]["info"]["cnname"]
    should_write = True
    for y in final_year:
        if y <= 1900:
            final_year.remove(y)
            logging.warning("%s is %s, popping %s", name, final_year, y)

    col.update_one({"data.info.id": _id}, {"$set": {"data.info.year": final_year}})
