#!/usr/bin/env python3
# coding: utf-8

# YYeTsBot - __init__.py
# 2023-03-17  18:57

import logging
import pathlib
import sys

from common.utils import Cloudflare, setup_logger

cf = Cloudflare()

setup_logger()

DOUBAN_SEARCH = "https://www.douban.com/search?cat=1002&q={}"
DOUBAN_DETAIL = "https://movie.douban.com/subject/{}/"

lib_path = (
    pathlib.Path(__file__)
    .parent.parent.parent.joinpath("yyetsbot")
    .resolve()
    .as_posix()
)

sys.path.append(lib_path)
from fansub import BD2020, XL720, NewzmzOnline, ZhuixinfanOnline, ZimuxiaOnline

logging.info(
    "Loading fansub...%s",
    (BD2020, XL720, NewzmzOnline, ZhuixinfanOnline, ZimuxiaOnline),
)
