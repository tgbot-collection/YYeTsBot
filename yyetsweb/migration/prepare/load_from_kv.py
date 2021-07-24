#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - load_from_kv.py
# 2/6/21 18:27
#

__author__ = "Benny <benny.think@gmail.com>"

import json
import os

import pymongo

mongo_client = pymongo.MongoClient()

data_files = [i for i in os.listdir("data/") if i.endswith(".json")]
col = mongo_client["zimuzu"]["yyets"]
for data_file in data_files:
    with open(os.path.join("data", data_file)) as f:
        d = json.load(f)
        views = int(d["data"]["info"]["views"])
        d["data"]["info"]["views"] = views
        col.insert_one(d)
