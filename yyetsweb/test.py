#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - test.py
# 5/31/21 13:32
#

__author__ = "Benny <benny.think@gmail.com>"

import pymongo

client = pymongo.MongoClient()
db = client["zimuzu"]
col = db["comment"]

for i in range(1, 18):
    data = {
        "username": "Benny",
        "ip": "127.0.0.1",
        "date": "Mon May 31 16:58:21 2021",
        "browser": "PostmanRuntime/7.28.0",
        "content": f"评论{i}",
        "id": i,
        "resource_id": 10004
    }
    col.insert_one(data)
