#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - change_datetime.py
# 6/15/21 14:15
#

__author__ = "Benny <benny.think@gmail.com>"

import pymongo
import time

client = pymongo.MongoClient()
from bson import ObjectId

comment = client["zimuzu"]["comment"]  # date
users = client["zimuzu"]["users"]  # date

all_comments = list(comment.find())
all_users = list(users.find())

for item in all_comments:
    object_id = item["_id"]
    old_date = time.strptime(item["date"], "%a %b %d %H:%M:%S %Y")
    new_date = time.strftime("%Y-%m-%d %H:%M:%S", old_date)

    condition = {"_id": object_id}
    update = {"$set": {"date": new_date}}
    comment.find_one_and_update(condition, update)

for item in all_users:
    # unique for username
    object_id = item["_id"]
    old_date = time.strptime(item["date"], "%a %b %d %H:%M:%S %Y")
    new_date = time.strftime("%Y-%m-%d %H:%M:%S", old_date)

    condition = {"_id": object_id}
    update = {"$set": {"date": new_date}}
    users.find_one_and_update(condition, update)
