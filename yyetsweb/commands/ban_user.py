#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - ban_user.py
# 3/26/22 10:26
#

__author__ = "Benny <benny.think@gmail.com>"

from common import Mongo
from tqdm import tqdm

client = Mongo()
user_col = client.db["users"]

with open("ban_user.txt", "r") as f:
    for line in tqdm(f, desc="Banning user..."):
        user, reason = line.split(maxsplit=1)
        ban = {"disable": True, "reason": reason}
        user_col.update_one({"username": user}, {"$set": {"status": ban}})

print("Done!")
