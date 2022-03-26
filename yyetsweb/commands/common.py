#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - common.py
# 3/26/22 10:40
#

__author__ = "Benny <benny.think@gmail.com>"

import pymongo
import os


class Mongo:
    def __init__(self):
        self.client = pymongo.MongoClient(host=os.getenv("mongo") or "localhost", connect=False,
                                          connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
        self.db = self.client["zimuzu"]

    def __del__(self):
        self.client.close()
