#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - format_order.py
# 2/9/21 16:24
#

__author__ = "Benny <benny.think@gmail.com>"

import pymongo

client = pymongo.MongoClient(host="mongo")
db = client["zimuzu"]
col = db["yyets"]

all_data = col.find().sort("data.info.id")

for resource in all_data:
    for index in range(len(resource["data"]["list"])):
        season = resource["data"]["list"][index]
        if season["formats"][0] == "APP":
            order = season["formats"][1:]
            order.append("APP")
            rid = resource["data"]["info"]["id"]
            set_value = {"$set": {f"data.list.{index}.formats": order}}
            print(f"{rid}-{index}->{set_value}")
            col.find_one_and_update({"data.info.id": rid}, set_value)
client.close()
