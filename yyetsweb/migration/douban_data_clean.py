#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - douban_data.py
# 7/24/21 19:28
#

__author__ = "Benny <benny.think@gmail.com>"

import logging
import pathlib
import sys

logging.basicConfig(level=logging.INFO)
lib_path = pathlib.Path(__file__).parent.parent.resolve().as_posix()
sys.path.append(lib_path)
from tqdm import tqdm

from Mongo import DoubanMongoResource

m = DoubanMongoResource()

m.db["douban"].update_many({}, {"$unset": {"raw": ""}})
logging.info("raw data deleted.")
# only writers are wrong
# wrong_field = ["actors", "directors", "genre", "writers"]
wrong_field = ["writers"]
# String 2 "string" 4 array
for field in wrong_field:
    incorrect_data = m.db["douban"].find({field: {"$not": {"$type": 4}}})
    for datum in tqdm(incorrect_data):
        logging.info("fixing %s", datum)
        new_field = datum[field].split()
        m.db["douban"].update_one({"_id": datum["_id"]}, {"$set": {field: new_field}})


logging.info("finish")