#!/usr/bin/env python3
# coding: utf-8

# YYeTsBot - __init__.py
# 2023-03-17  18:57

import logging
import os
import pathlib
import sys

import pymongo

DOUBAN_SEARCH = "https://www.douban.com/search?cat=1002&q={}"
DOUBAN_DETAIL = "https://movie.douban.com/subject/{}/"

lib_path = pathlib.Path(__file__).parent.parent.parent.joinpath("yyetsbot").resolve().as_posix()

sys.path.append(lib_path)
from fansub import BD2020, XL720, NewzmzOnline, ZhuixinfanOnline, ZimuxiaOnline

logging.info(
    "Initialized: loading fansub...%s",
    (BD2020, XL720, NewzmzOnline, ZhuixinfanOnline, ZimuxiaOnline),
)

client = pymongo.MongoClient(
    host=os.getenv("MONGO", "localhost"),
    connect=True,
    connectTimeoutMS=5000,
    serverSelectionTimeoutMS=5000,
    maxPoolSize=300,
    minPoolSize=50,
    maxIdleTimeMS=600000,
)
db = client["zimuzu"]
