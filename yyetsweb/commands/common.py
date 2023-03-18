#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - common.py
# 3/26/22 10:40
#

__author__ = "Benny <benny.think@gmail.com>"

import os

import pymongo


class Mongo:
    def __init__(self):
        self.client = pymongo.MongoClient(
            host=os.getenv("MONGO", "localhost"),
            connect=False,
            connectTimeoutMS=5000,
            serverSelectionTimeoutMS=5000,
        )
        self.db = self.client["zimuzu"]

    def __del__(self):
        self.client.close()
