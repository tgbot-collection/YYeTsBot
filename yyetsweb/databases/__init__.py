#!/usr/bin/env python3
# coding: utf-8

# YYeTsBot - __init__.py
# 2023-03-17  18:57

import logging
import os
import pathlib
import sys

import fakeredis
import pymongo
import redis

DOUBAN_SEARCH = "https://www.douban.com/search?cat=1002&q={}"
DOUBAN_DETAIL = "https://movie.douban.com/subject/{}/"

lib_path = pathlib.Path(__file__).parent.parent.parent.joinpath("yyetsbot").resolve().as_posix()

sys.path.append(lib_path)
from fansub import BD2020, XL720, NewzmzOnline, ZhuixinfanOnline, ZimuxiaOnline

logging.info(
    "Initialized: loading fansub...%s",
    (BD2020, XL720, NewzmzOnline, ZhuixinfanOnline, ZimuxiaOnline),
)

mongo_client = pymongo.MongoClient(
    host=os.getenv("MONGO", "localhost"),
    connect=True,
    connectTimeoutMS=5000,
    serverSelectionTimeoutMS=5000,
    maxPoolSize=300,
    minPoolSize=50,
    maxIdleTimeMS=600000,
)
db = mongo_client["zimuzu"]

try:
    redis_client = redis.StrictRedis(
        host=os.getenv("REDIS", "localhost"),
        decode_responses=True,
        max_connections=100,
    )
    redis_client.ping()
except redis.exceptions.ConnectionError:
    logging.warning("%s Using fakeredis now... %s", "#" * 10, "#" * 10)
    redis_client = fakeredis.FakeStrictRedis()
