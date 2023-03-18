#!/usr/bin/env python3
# coding: utf-8
import json

from tornado import escape

from common.utils import Cloudflare, setup_logger

setup_logger()
cf = Cloudflare()
escape.json_encode = lambda value: json.dumps(value, ensure_ascii=False)
